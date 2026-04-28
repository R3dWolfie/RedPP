#!/usr/bin/env python3
"""redpp — EZPP-style osu!(lazer) pp calculator (one-shot / REPL / watch)."""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path

import rosu_pp_py as rosu

KNOWN_MODS = {"EZ","NF","HT","DC","HR","SD","PF","DT","NC","HD",
              "FL","RX","AP","SO","TD","CL","BL","TC"}
DEFAULT_ACC_PRESETS = (95.0, 97.0, 99.0, 100.0)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 24050
POLL_INTERVAL = 0.5

IS_TTY = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
def _c(code: str, s: str) -> str:
    return f"\x1b[{code}m{s}\x1b[0m" if IS_TTY else s
CYAN  = lambda s: _c("36", s)
GREEN = lambda s: _c("1;32", s)
YELL  = lambda s: _c("33", s)
DIM   = lambda s: _c("2", s)
BOLD  = lambda s: _c("1", s)


@dataclass
class ParsedScore:
    mods: str = ""
    accuracy: float | None = None
    n300: int | None = None
    n100: int | None = None
    n50:  int | None = None
    misses: int | None = None
    combo: int | None = None
    ar: float | None = None
    od: float | None = None
    cs: float | None = None
    hp: float | None = None
    fixed_ar: bool = False
    fixed_od: bool = False
    fixed_cs: bool = False
    fixed_hp: bool = False
    clock_rate: float | None = None
    lazer: bool = True

    def is_bare_mods(self) -> bool:
        """True when only mods/diff/rate were given — render preset row."""
        return (self.accuracy is None and self.n300 is None and self.n100 is None
                and self.n50 is None and self.misses is None and self.combo is None)


_RE_DIFF      = re.compile(r"\b(ar|od|cs|hp)(\d+(?:\.\d+)?)\b", re.I)
_RE_CLOCK     = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)x(?![\w.])", re.I)
_RE_HITS      = re.compile(r"(\d+)x(50|100|300|miss|m)\b", re.I)
_RE_COMBO_LX  = re.compile(r"\bx(\d+)\b")
_RE_COMBO_RX  = re.compile(r"\b(\d+)x\b")
_RE_ACC       = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_RE_ALPHA_TOK = re.compile(r"\b([A-Za-z]+)\b")


def parse_score_string(s: str) -> ParsedScore:
    out = ParsedScore()
    text = " " + s.strip() + " "

    # 1. stable / lazer keywords
    if re.search(r"\bstable\b", text, re.I):
        out.lazer = False
        text = re.sub(r"\bstable\b", " ", text, flags=re.I)
    if re.search(r"\blazer\b", text, re.I):
        out.lazer = True
        text = re.sub(r"\blazer\b", " ", text, flags=re.I)

    # 2. diff overrides ar/od/cs/hp
    def _diff_sub(m):
        key, val = m.group(1).lower(), float(m.group(2))
        setattr(out, key, val)
        return " "
    text = _RE_DIFF.sub(_diff_sub, text)

    # 4. hits FIRST (so 8x50 isn't misread as clock rate)
    def _hit_sub(m):
        n = int(m.group(1))
        kind = m.group(2).lower()
        if kind == "50":
            out.n50 = n
        elif kind == "100":
            out.n100 = n
        elif kind == "300":
            out.n300 = n
        else:  # m / miss
            out.misses = n
        return " "
    text = _RE_HITS.sub(_hit_sub, text)

    # 3. clock rate (after hits stripped). Sanity-check 0.5..3.0.
    def _clock_sub(m):
        v = float(m.group(1))
        if 0.5 <= v <= 3.0:
            out.clock_rate = v
            return " "
        return m.group(0)
    text = _RE_CLOCK.sub(_clock_sub, text)

    # 5. combo (only AFTER hits stripped)
    m = _RE_COMBO_LX.search(text)
    if m:
        out.combo = int(m.group(1))
        text = text[:m.start()] + " " + text[m.end():]
    else:
        m = _RE_COMBO_RX.search(text)
        if m:
            out.combo = int(m.group(1))
            text = text[:m.start()] + " " + text[m.end():]

    # 6. accuracy
    m = _RE_ACC.search(text)
    if m:
        out.accuracy = float(m.group(1))
        text = text[:m.start()] + " " + text[m.end():]

    # 7. remaining alpha tokens → mods (chunk into 2-char pairs)
    mods: list[str] = []
    for m in _RE_ALPHA_TOK.finditer(text):
        word = m.group(1).upper()
        if len(word) % 2 != 0:
            # odd-length token that isn't a keyword we already handled → error
            hint = get_close_matches(word, KNOWN_MODS, n=1)
            extra = f" (did you mean {hint[0]}?)" if hint else ""
            raise ValueError(f"unknown mod '{word}'{extra}")
        for i in range(0, len(word), 2):
            tok = word[i:i+2]
            if tok not in KNOWN_MODS:
                hint = get_close_matches(tok, KNOWN_MODS, n=1)
                extra = f" (did you mean {hint[0]}?)" if hint else ""
                raise ValueError(f"unknown mod '{tok}'{extra}")
            if tok not in mods:
                mods.append(tok)
    out.mods = "".join(mods)

    # default misses to 0 only when accuracy AND at least one hit count provided
    has_hits = out.n50 is not None or out.n100 is not None or out.n300 is not None
    if out.accuracy is not None and has_hits:
        out.n50 = out.n50 or 0
        out.n100 = out.n100 or 0
        out.n300 = out.n300 or 0
        out.misses = out.misses or 0

    return out


@dataclass
class RenderData:
    filename: str
    stars: float
    ar: float
    od: float
    cs: float
    hp: float
    bpm: float
    clock_rate: float
    mods_str: str
    combo: int | None
    max_combo: int
    n300: int
    n100: int
    n50: int
    misses: int
    accuracy: float
    pp: float
    pp_aim: float
    pp_speed: float
    pp_acc: float
    pp_difficulty: float
    pp_flashlight: float


_BMAP_CACHE: dict[tuple[str, float], "rosu.Beatmap"] = {}


def load_bmap(path: str) -> "rosu.Beatmap":
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"map not found: {path}")
    key = (str(p.resolve()), p.stat().st_mtime)
    cached = _BMAP_CACHE.get(key)
    if cached is not None:
        return cached
    bmap = rosu.Beatmap(path=str(p))
    if bmap.is_suspicious():
        raise RuntimeError("(suspicious — skipping)")
    # opportunistic eviction: keep cache small
    if len(_BMAP_CACHE) > 32:
        _BMAP_CACHE.clear()
    _BMAP_CACHE[key] = bmap
    return bmap


def _build_perf_kwargs(score: ParsedScore) -> dict:
    kw: dict = {"lazer": score.lazer}
    if score.mods:
        kw["mods"] = score.mods
    if score.clock_rate is not None:
        kw["clock_rate"] = score.clock_rate
    if score.ar is not None:
        kw["ar"] = score.ar; kw["fixed_ar"] = score.fixed_ar
    if score.od is not None:
        kw["od"] = score.od; kw["fixed_od"] = score.fixed_od
    if score.cs is not None:
        kw["cs"] = score.cs; kw["fixed_cs"] = score.fixed_cs
    if score.hp is not None:
        kw["hp"] = score.hp; kw["fixed_hp"] = score.fixed_hp
    return kw


def _build_attrs(bmap: "rosu.Beatmap", score: ParsedScore):
    bab_kw: dict = {"map": bmap}
    if score.mods:
        bab_kw["mods"] = score.mods
    if score.clock_rate is not None:
        bab_kw["clock_rate"] = score.clock_rate
    if score.ar is not None: bab_kw["ar"] = score.ar
    if score.od is not None: bab_kw["od"] = score.od
    if score.cs is not None: bab_kw["cs"] = score.cs
    if score.hp is not None: bab_kw["hp"] = score.hp
    return rosu.BeatmapAttributesBuilder(**bab_kw).build()


def _render_data(path: str, bmap, attrs, score: ParsedScore,
                  perf_attrs, accuracy: float) -> RenderData:
    diff = perf_attrs.difficulty
    return RenderData(
        filename=Path(path).name,
        stars=diff.stars,
        ar=attrs.ar, od=attrs.od, cs=attrs.cs, hp=attrs.hp,
        bpm=bmap.bpm * attrs.clock_rate,
        clock_rate=attrs.clock_rate,
        mods_str=score.mods,
        combo=score.combo,
        max_combo=diff.max_combo,
        n300=score.n300 or 0,
        n100=score.n100 or 0,
        n50=score.n50 or 0,
        misses=score.misses or 0,
        accuracy=accuracy,
        pp=perf_attrs.pp,
        pp_aim=perf_attrs.pp_aim or 0.0,
        pp_speed=perf_attrs.pp_speed or 0.0,
        pp_acc=perf_attrs.pp_accuracy or 0.0,
        pp_difficulty=perf_attrs.pp_difficulty or 0.0,
        pp_flashlight=perf_attrs.pp_flashlight or 0.0,
    )


def calc_one(path: str, score: ParsedScore) -> RenderData:
    bmap = load_bmap(path)
    attrs = _build_attrs(bmap, score)
    kw = _build_perf_kwargs(score)
    if score.accuracy is not None:
        kw["accuracy"] = score.accuracy
    if score.n300 is not None: kw["n300"] = score.n300
    if score.n100 is not None: kw["n100"] = score.n100
    if score.n50  is not None: kw["n50"]  = score.n50
    if score.misses is not None: kw["misses"] = score.misses
    if score.combo is not None: kw["combo"] = score.combo
    perf = rosu.Performance(**kw).calculate(bmap)

    # derive accuracy if not specified (calculated from hit counts by rosu-pp's state)
    acc = score.accuracy
    if acc is None:
        st = perf.state
        total = (st.n300 + st.n100 + st.n50 + st.misses) or 1
        acc = (300*st.n300 + 100*st.n100 + 50*st.n50) / (300 * total) * 100.0
    return _render_data(path, bmap, attrs, score, perf, acc)


def calc_presets(path: str, score: ParsedScore,
                  accs: tuple[float, ...]) -> tuple[RenderData, list[RenderData]]:
    bmap = load_bmap(path)
    attrs = _build_attrs(bmap, score)
    base_kw = _build_perf_kwargs(score)
    rows: list[RenderData] = []
    header_rd: RenderData | None = None
    for a in accs:
        kw = dict(base_kw)
        kw["accuracy"] = a
        perf = rosu.Performance(**kw).calculate(bmap)
        rd = _render_data(path, bmap, attrs, score, perf, a)
        if header_rd is None:
            header_rd = rd
        rows.append(rd)
    assert header_rd is not None
    return header_rd, rows


def _fmt_rate(rate: float) -> str:
    return f"  ({rate:.2f}x)" if abs(rate - 1.0) > 1e-3 else ""


def _hits_str(rd: RenderData) -> str:
    parts = []
    if rd.n300: parts.append(f"{rd.n300}x300")
    if rd.n100: parts.append(f"{rd.n100}x100")
    if rd.n50:  parts.append(f"{rd.n50}x50")
    if rd.misses: parts.append(f"{rd.misses}xMiss")
    return " ".join(parts) if parts else "-"


def _header_lines(rd: RenderData) -> list[str]:
    return [
        rd.filename,
        f"{CYAN(f'{rd.stars:.2f}*')}   "
        f"AR {rd.ar:.1f}  OD {rd.od:.1f}  CS {rd.cs:.1f}  HP {rd.hp:.1f}  "
        f"BPM {rd.bpm:.0f}{_fmt_rate(rd.clock_rate)}",
    ]


def _verbose_line(rd: RenderData) -> str:
    return DIM(f"  aim {rd.pp_aim:.1f} | speed {rd.pp_speed:.1f} | "
               f"acc {rd.pp_acc:.1f} | diff {rd.pp_difficulty:.1f} | fl {rd.pp_flashlight:.1f}")


def render_oneshot(rd: RenderData, *, verbose: bool, as_json: bool, pinned: bool = False) -> str:
    if as_json:
        return json.dumps({
            "filename": rd.filename, "stars": rd.stars,
            "ar": rd.ar, "od": rd.od, "cs": rd.cs, "hp": rd.hp,
            "bpm": rd.bpm, "clock_rate": rd.clock_rate,
            "mods": rd.mods_str, "combo": rd.combo, "max_combo": rd.max_combo,
            "hits": {"n300": rd.n300, "n100": rd.n100, "n50": rd.n50, "miss": rd.misses},
            "acc": rd.accuracy, "pp": rd.pp,
            "pp_aim": rd.pp_aim, "pp_speed": rd.pp_speed, "pp_acc": rd.pp_acc,
            "pp_difficulty": rd.pp_difficulty, "pp_flashlight": rd.pp_flashlight,
        })
    lines = _header_lines(rd)
    pin = " [pinned]" if pinned else ""
    mods_disp = rd.mods_str or "NM"
    combo_disp = (f"{rd.combo}/{rd.max_combo}x" if rd.combo is not None
                  else f"{rd.max_combo}x")
    info = (f"mods: {YELL(mods_disp)}{pin}    "
            f"combo: {combo_disp}   "
            f"hits: {_hits_str(rd)}   "
            f"acc: {rd.accuracy:.2f}%")
    lines.append(info)
    if verbose:
        lines.append(_verbose_line(rd))
    lines.append(f"-> {GREEN(f'{rd.pp:.2f}pp')}")
    return "\n".join(lines)


def render_presets(header: RenderData, rows: list[RenderData], *,
                    verbose: bool, as_json: bool, pinned: bool = False) -> str:
    if as_json:
        return json.dumps({
            "filename": header.filename, "stars": header.stars,
            "ar": header.ar, "od": header.od, "cs": header.cs, "hp": header.hp,
            "bpm": header.bpm, "clock_rate": header.clock_rate,
            "mods": header.mods_str, "max_combo": header.max_combo,
            "presets": [{"acc": r.accuracy, "pp": r.pp} for r in rows],
        })
    lines = _header_lines(header)
    mods_disp = header.mods_str or "NM"
    pin = " [pinned]" if pinned else ""
    lines.append(f"mods: {YELL(mods_disp)}{pin}    combo: {header.max_combo}x")
    preset_parts = [f"{r.accuracy:g}%: {GREEN(f'{r.pp:.0f}pp')}" for r in rows]
    lines.append("   ".join(preset_parts))
    if verbose:
        lines.append(_verbose_line(header))
    return "\n".join(lines)


def _parse_acc_arg(s: str | None) -> tuple[float, ...]:
    if not s:
        return DEFAULT_ACC_PRESETS
    try:
        return tuple(float(x.strip()) for x in s.split(","))
    except ValueError:
        raise ValueError(f"invalid --acc list: {s!r}")


def run_oneshot(map_path: str, score_str: str, *, verbose: bool, as_json: bool,
                accs: tuple[float, ...]) -> int:
    score = parse_score_string(score_str)
    if score.is_bare_mods():
        header, rows = calc_presets(map_path, score, accs)
        print(render_presets(header, rows, pinned=False, verbose=verbose, as_json=as_json))
    else:
        rd = calc_one(map_path, score)
        print(render_oneshot(rd, verbose=verbose, as_json=as_json))
    return 0


@dataclass
class TosuState:
    path: str
    mods_str: str


class TosuClient:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = 1.5) -> None:
        self.base = f"http://{host}:{port}"
        self.timeout = timeout

    def _get(self, path: str) -> dict | None:
        url = f"{self.base}{path}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as r:
                if r.status != 200:
                    return None
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError:
            return None
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            raise ConnectionError(f"tosu unreachable at {self.base}: {e}") from e

    def fetch_state(self) -> TosuState | None:
        data = self._get("/api/v2")
        if data is not None:
            st = self._parse_v2(data)
            if st is not None:
                return st
        data = self._get("/json")
        if data is not None:
            return self._parse_json(data)
        return None

    @staticmethod
    def _parse_v2(d: dict) -> TosuState | None:
        bm = (d.get("beatmap") or {})
        path_obj = (bm.get("path") or {})
        full = path_obj.get("full") or ""
        if full and Path(full).is_file():
            return TosuState(path=full, mods_str=TosuClient._extract_mods(d))
        folder = path_obj.get("folder") or ""
        file_ = path_obj.get("file") or ""
        if not (folder and file_):
            return None
        if Path(folder).is_absolute():
            p = Path(folder) / file_
        else:
            songs = ((d.get("folders") or {}).get("beatmap")
                     or (d.get("folders") or {}).get("songs") or "")
            if not songs:
                return None
            p = Path(songs) / folder / file_
        if not p.is_file():
            return None
        return TosuState(path=str(p), mods_str=TosuClient._extract_mods(d))

    @staticmethod
    def _parse_json(d: dict) -> TosuState | None:
        menu = d.get("menu") or {}
        bm = menu.get("bm") or {}
        path_obj = bm.get("path") or {}
        folder = path_obj.get("folder") or ""
        file_ = path_obj.get("file") or ""
        if not (folder and file_):
            return None
        if Path(folder).is_absolute():
            p = Path(folder) / file_
        else:
            songs = ((d.get("settings") or {}).get("folders") or {}).get("songs") or ""
            if not songs:
                return None
            p = Path(songs) / folder / file_
        if not p.is_file():
            return None
        return TosuState(path=str(p), mods_str=TosuClient._extract_mods_json(d))

    @staticmethod
    def _extract_mods(d: dict) -> str:
        for branch in ("play", "menu"):
            mods = ((d.get(branch) or {}).get("mods") or {})
            arr = mods.get("array")
            if arr:
                acronyms = [m.get("acronym", "") for m in arr if isinstance(m, dict)]
                joined = "".join(a for a in acronyms if a)
                if joined: return joined
            for k in ("name", "acronym", "str"):
                v = mods.get(k)
                if v:
                    return "".join(re.findall(r"[A-Za-z]{2}", v)).upper()
        return ""

    @staticmethod
    def _extract_mods_json(d: dict) -> str:
        mods = ((d.get("menu") or {}).get("mods") or {})
        v = mods.get("str") or mods.get("name") or ""
        return "".join(re.findall(r"[A-Za-z]{2}", v)).upper()

def run_repl(map_path: str, *, accs: tuple[float, ...],
             verbose: bool, as_json: bool) -> int:
    try:
        import readline  # noqa: F401  - enables ↑/↓ and line editing
        readline.set_history_length(500)
    except ImportError:
        pass
    last_score: ParsedScore | None = None
    last_path = map_path
    print(DIM(f"redpp REPL — map: {Path(last_path).name}  (Ctrl-D to exit)"))
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            if last_score is None:
                # render preset row for current map+nomod
                try:
                    header, rows = calc_presets(last_path, ParsedScore(), accs)
                    print(render_presets(header, rows, pinned=False,
                                          verbose=verbose, as_json=as_json))
                except (ValueError, FileNotFoundError, RuntimeError) as e:
                    print(f"error: {e}", file=sys.stderr)
            else:
                # re-render with last score
                try:
                    if last_score.is_bare_mods():
                        header, rows = calc_presets(last_path, last_score, accs)
                        print(render_presets(header, rows, pinned=False,
                                              verbose=verbose, as_json=as_json))
                    else:
                        rd = calc_one(last_path, last_score)
                        print(render_oneshot(rd, verbose=verbose, as_json=as_json))
                except (ValueError, FileNotFoundError, RuntimeError) as e:
                    print(f"error: {e}", file=sys.stderr)
            continue
        try:
            score = parse_score_string(line)
            if score.is_bare_mods():
                header, rows = calc_presets(last_path, score, accs)
                print(render_presets(header, rows, pinned=False,
                                      verbose=verbose, as_json=as_json))
            else:
                rd = calc_one(last_path, score)
                print(render_oneshot(rd, verbose=verbose, as_json=as_json))
            last_score = score
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            print(f"error: {e}", file=sys.stderr)

def run_watch(map_path: str | None, *, mods_override: str | None,
              accs: tuple[float, ...], host: str, port: int,
              verbose: bool, as_json: bool, quiet: bool) -> int:
    client = TosuClient(host, port)
    last_key: tuple[str, str] | None = None
    no_map_shown = False
    unreachable_shown = False
    backoff = POLL_INTERVAL
    if mods_override is not None:
        try:
            parse_score_string(mods_override)  # validate
        except ValueError as e:
            print(f"error: bad --mods: {e}", file=sys.stderr); return 2

    try:
        while True:
            try:
                state = client.fetch_state()
                if unreachable_shown:
                    if IS_TTY: sys.stdout.write("\r\x1b[2K")
                    unreachable_shown = False
                    backoff = POLL_INTERVAL
            except ConnectionError:
                if not unreachable_shown:
                    print(DIM("(tosu unreachable, retrying…)"))
                    unreachable_shown = True
                time.sleep(backoff)
                backoff = min(backoff * 2, 5.0)
                continue

            override_path = map_path  # CLI-passed path overrides tosu

            if state is None and override_path is None:
                if not no_map_shown:
                    print("(no map)")
                    no_map_shown = True
                last_key = None
                time.sleep(POLL_INTERVAL); continue
            no_map_shown = False

            path = override_path or state.path
            mods_str = mods_override if mods_override is not None else (state.mods_str if state else "")
            key = (path, mods_str)
            if key != last_key:
                try:
                    score = parse_score_string(mods_str) if mods_str else ParsedScore()
                    header, rows = calc_presets(path, score, accs)
                    print(render_presets(header, rows,
                                          pinned=mods_override is not None,
                                          verbose=verbose, as_json=as_json))
                except RuntimeError as e:
                    print(f"({e})")
                except (ValueError, FileNotFoundError) as e:
                    print(f"error: {e}", file=sys.stderr)
                last_key = key

            if not quiet and IS_TTY:
                ts = time.strftime("%H:%M:%S")
                sys.stdout.write(f"\r{DIM(f'(polling {port} · {ts})')}")
                sys.stdout.flush()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        if IS_TTY and not quiet:
            sys.stdout.write("\r\x1b[2K")
        print()
        return 0

def _self_test() -> int:
    """Minimal parser regression — runs without pytest."""
    cases: list[tuple[str, dict]] = [
        ("HDHR 94.30% 8x50 42x100 700x300",
         {"mods": "HDHR", "accuracy": 94.30, "n50": 8, "n100": 42, "n300": 700}),
        ("HDDT 98.5% 5xMiss x650",
         {"mods": "HDDT", "misses": 5, "combo": 650}),
        ("1.3x 99% ar10",
         {"clock_rate": 1.3, "ar": 10.0, "accuracy": 99.0}),
        ("100%", {"accuracy": 100.0, "mods": ""}),
        ("HDHR", {"mods": "HDHR", "accuracy": None}),
    ]
    failed = 0
    for s, expect in cases:
        try:
            r = parse_score_string(s)
            for k, v in expect.items():
                got = getattr(r, k)
                if got != v:
                    print(f"FAIL {s!r}: {k} expected {v!r}, got {got!r}", file=sys.stderr)
                    failed += 1; break
            else:
                print(f"ok   {s!r}")
        except Exception as e:
            print(f"FAIL {s!r}: raised {type(e).__name__}: {e}", file=sys.stderr); failed += 1
    # error case
    try:
        parse_score_string("ZZ 99%")
        print("FAIL: 'ZZ 99%' should have raised", file=sys.stderr); failed += 1
    except ValueError:
        print("ok   'ZZ 99%' raised as expected")
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="redpp", description="EZPP-style osu!(lazer) pp calculator")
    ap.add_argument("map", nargs="?", help=".osu file path (omit to fetch from tosu)")
    ap.add_argument("score", nargs="?", help='score string e.g. "HDHR 94.30%% 8x50 42x100 700x300"')
    ap.add_argument("-w", "--watch", action="store_true", help="auto-poll tosu, re-render on change")
    ap.add_argument("--mods", help="pin mods in watch mode (e.g. HDHR)")
    ap.add_argument("--acc", help="comma-separated acc presets (default 95,97,99,100)")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--json", dest="as_json", action="store_true", help="machine-readable output")
    ap.add_argument("--verbose", action="store_true", help="show pp_aim/speed/acc breakdown")
    ap.add_argument("--quiet", action="store_true", help="hide watch-mode footer")
    ap.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        accs = _parse_acc_arg(args.acc)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr); return 2

    if args.self_test:
        return _self_test()

    if args.watch:
        return run_watch(args.map, mods_override=args.mods, accs=accs,
                          host=args.host, port=args.port,
                          verbose=args.verbose, as_json=args.as_json,
                          quiet=args.quiet)

    map_path = args.map
    if map_path is None:
        # tosu auto-fetch (Task 7)
        client = TosuClient(args.host, args.port)
        try:
            st = client.fetch_state()
        except Exception as e:
            print(f"error: tosu fetch failed: {e}", file=sys.stderr); return 1
        if st is None:
            print("error: tosu has no current map", file=sys.stderr); return 1
        map_path = st.path

    if args.score is None:
        return run_repl(map_path, accs=accs, verbose=args.verbose, as_json=args.as_json)

    try:
        return run_oneshot(map_path, args.score, verbose=args.verbose,
                            as_json=args.as_json, accs=accs)
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr); return 1


if __name__ == "__main__":
    sys.exit(main())
