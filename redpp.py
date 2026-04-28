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
_RE_MOD       = re.compile(r"\b([A-Za-z]{2})\b")


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

    # set fixed_* flags for any diff override given
    if out.ar is not None: out.fixed_ar = False
    if out.od is not None: out.fixed_od = False
    if out.cs is not None: out.fixed_cs = False
    if out.hp is not None: out.fixed_hp = False

    # 7. remaining alpha tokens → mods (chunk into 2-char pairs)
    mods: list[str] = []
    _RE_ALPHA_TOK = re.compile(r"\b([A-Za-z]+)\b")
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
    print("redpp skeleton — args:", args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
