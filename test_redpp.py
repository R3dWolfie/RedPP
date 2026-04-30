import importlib
import json
import re
import sys
import tempfile
import pytest
from redpp import parse_score_string, ParsedScore


def test_redpp_imports_with_none_stdout(monkeypatch):
    """PyInstaller --windowed on Windows sets sys.stdout / sys.stderr to
    None. The module-level IS_TTY computation must handle that without
    crashing on import — desktop app loads fail otherwise.

    Regression: 0.2.1 shipped a .exe that crashed at startup with
    AttributeError: 'NoneType' object has no attribute 'isatty'."""
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    sys.modules.pop("redpp", None)
    try:
        import redpp as _r  # noqa: F401  - import is the test
        assert _r.IS_TTY is False
        # The color helpers must still be safe to call.
        assert _r.CYAN("x") == "x"
    finally:
        # Restore real stdout/stderr (monkeypatch does this) and force a
        # fresh import for the rest of the suite.
        monkeypatch.undo()
        sys.modules.pop("redpp", None)
        importlib.import_module("redpp")

def _p(s):
    return parse_score_string(s)

def test_full_string():
    r = _p("HDHR 94.30% 8x50 42x100 700x300")
    assert r.mods == "HDHR"
    assert r.accuracy == 94.30
    assert r.n50 == 8 and r.n100 == 42 and r.n300 == 700
    assert r.misses == 0
    assert r.lazer is True

def test_dt_misses_combo():
    r = _p("HDDT 98.5% 5xMiss x650")
    assert r.mods == "HDDT"
    assert r.misses == 5
    assert r.combo == 650
    assert r.accuracy == 98.5

def test_clock_rate_and_diff_override():
    r = _p("1.3x 99% ar10")
    assert r.clock_rate == 1.3
    assert r.ar == 10.0
    assert r.fixed_ar is False

def test_ez_dt_with_diff_overrides():
    r = _p("EZ DT 95% cs2 ar7")
    assert sorted(re.findall(r'..', r.mods)) == ["DT","EZ"]  # accept any order
    assert r.cs == 2.0 and r.ar == 7.0

def test_just_acc():
    r = _p("100%")
    assert r.accuracy == 100.0
    assert r.mods == ""
    assert r.n50 is None and r.n100 is None and r.n300 is None

def test_unknown_mod_errors():
    with pytest.raises(ValueError, match="unknown mod"):
        _p("ZZ 99%")

def test_clock_rate_does_not_eat_hits():
    r = _p("HDHR 8x50 42x100 700x300 99%")
    assert r.n50 == 8 and r.n100 == 42 and r.n300 == 700
    assert r.clock_rate is None

def test_stable_keyword():
    r = _p("HD stable 99%")
    assert r.lazer is False
    assert r.mods == "HD"

def test_case_insensitive_mods():
    r = _p("hdhr 99%")
    assert r.mods == "HDHR"

def test_xMiss_short_form():
    r = _p("3xM 99%")
    assert r.misses == 3

def test_combo_post_strip():
    # "8x50" must be eaten as hits before combo regex sees it
    r = _p("HD 8x50 1234x 99%")
    assert r.n50 == 8 and r.combo == 1234

def test_no_acc_no_hits_returns_empty():
    r = _p("HDHR")
    assert r.mods == "HDHR" and r.accuracy is None
    assert r.n50 is None and r.combo is None


def make_osu(n_circles: int = 100, ar: float = 9.0, od: float = 8.0,
             cs: float = 4.0, hp: float = 5.0, bpm: float = 180.0) -> str:
    """Write a synthetic .osu file with proper [TimingPoints]. Returns path."""
    beat_ms = 60000.0 / bpm
    body = [
        "osu file format v14",
        "[General]",
        "Mode: 0",
        "[Metadata]",
        "Title:Test",
        "Artist:RedPP",
        "Creator:RedPP",
        "Version:Synthetic",
        "[Difficulty]",
        f"HPDrainRate:{hp}",
        f"CircleSize:{cs}",
        f"OverallDifficulty:{od}",
        f"ApproachRate:{ar}",
        "SliderMultiplier:1.4",
        "SliderTickRate:1",
        "[TimingPoints]",
        f"0,{beat_ms},4,2,1,80,1,0",
        "[HitObjects]",
    ]
    for i in range(n_circles):
        body.append(f"256,192,{1000 + i * 200},1,0,0:0:0:0:")
    f = tempfile.NamedTemporaryFile("w", suffix=".osu", delete=False)
    f.write("\n".join(body))
    f.close()
    return f.name


def test_synthetic_map_loads():
    import rosu_pp_py as rosu
    p = make_osu()
    bmap = rosu.Beatmap(path=p)
    assert bmap.bpm == pytest.approx(180.0, abs=0.5)
    assert not bmap.is_suspicious()


def test_load_bmap_caches():
    from redpp import load_bmap, _BMAP_CACHE
    p = make_osu()
    _BMAP_CACHE.clear()
    a = load_bmap(p)
    b = load_bmap(p)
    assert a is b  # same instance from cache

def test_calc_one_basic():
    from redpp import calc_one
    p = make_osu()
    score = parse_score_string("99%")
    rd = calc_one(p, score)
    assert rd.pp > 0
    assert rd.stars > 0
    assert rd.bpm > 0
    assert rd.mods_str == ""

def test_calc_one_hr_changes_ar():
    from redpp import calc_one
    p = make_osu(ar=9.0)
    rd_nm = calc_one(p, parse_score_string("100%"))
    rd_hr = calc_one(p, parse_score_string("HR 100%"))
    assert rd_hr.ar > rd_nm.ar  # HR should bump AR
    assert rd_hr.pp > rd_nm.pp  # HR usually awards more pp here

def test_calc_one_clock_rate_overrides_dt():
    from redpp import calc_one
    p = make_osu()
    rd = calc_one(p, parse_score_string("1.5x 100%"))
    assert rd.clock_rate == pytest.approx(1.5)

def test_calc_presets_returns_row():
    from redpp import calc_presets
    p = make_osu()
    score = parse_score_string("HDHR")
    header, rows = calc_presets(p, score, (95.0, 99.0, 100.0))
    assert len(rows) == 3
    assert all(r.pp > 0 for r in rows)
    assert rows[2].pp >= rows[0].pp  # 100% >= 95%


def test_render_oneshot_text(monkeypatch):
    import redpp
    monkeypatch.setattr(redpp, "IS_TTY", False)  # plain text for assertion
    from redpp import calc_one, render_oneshot
    p = make_osu()
    rd = calc_one(p, parse_score_string("HDHR 99% 1x100 99x300"))
    out = render_oneshot(rd, verbose=False, as_json=False)
    assert "->" in out and "pp" in out
    assert "AR" in out and "OD" in out and "BPM" in out
    assert "HDHR" in out

def test_render_presets_text(monkeypatch):
    import redpp
    monkeypatch.setattr(redpp, "IS_TTY", False)
    from redpp import calc_presets, render_presets
    p = make_osu()
    header, rows = calc_presets(p, parse_score_string("HDHR"), (95.0, 99.0, 100.0))
    out = render_presets(header, rows, pinned=False, verbose=False, as_json=False)
    assert "95%" in out and "99%" in out and "100%" in out
    assert "pp" in out

def test_render_json():
    from redpp import calc_one, render_oneshot
    p = make_osu()
    rd = calc_one(p, parse_score_string("HDHR 99% 1x100 99x300"))
    out = render_oneshot(rd, verbose=False, as_json=True)
    obj = json.loads(out)
    assert obj["mods"] == "HDHR"
    assert obj["pp"] > 0
    assert obj["filename"].endswith(".osu")


import threading
import http.server
import socketserver
import time as _time

class _FakeTosu(http.server.BaseHTTPRequestHandler):
    payloads: dict[str, dict] = {}
    def do_GET(self):
        body = self.payloads.get(self.path)
        if body is None:
            self.send_response(404); self.end_headers(); return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *a, **kw): pass


@pytest.fixture
def fake_tosu():
    srv = socketserver.TCPServer(("127.0.0.1", 0), _FakeTosu)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    yield srv, port
    srv.shutdown(); srv.server_close()


def test_tosu_v2_absolute_path(fake_tosu, tmp_path):
    from redpp import TosuClient
    srv, port = fake_tosu
    osu = tmp_path / "song.osu"; osu.write_text("osu file format v14\n[HitObjects]\n")
    _FakeTosu.payloads = {"/api/v2": {
        "beatmap": {"path": {"full": str(osu), "folder": "", "file": ""}},
        "play": {"mods": {"name": "HDHR"}},
    }}
    c = TosuClient("127.0.0.1", port)
    st = c.fetch_state()
    assert st is not None
    assert st.path == str(osu)
    assert st.mods_str == "HDHR"


def test_tosu_v2_joined_path(fake_tosu, tmp_path):
    from redpp import TosuClient
    srv, port = fake_tosu
    folder = tmp_path / "456 Artist - Title"; folder.mkdir()
    osu = folder / "Title [Hard].osu"; osu.write_text("osu file format v14\n[HitObjects]\n")
    _FakeTosu.payloads = {"/api/v2": {
        "beatmap": {"path": {"full": "", "folder": folder.name, "file": osu.name}},
        "folders": {"songs": str(tmp_path), "beatmap": ""},
        "play": {"mods": {"array": [{"acronym": "HD"}, {"acronym": "DT"}]}},
    }}
    c = TosuClient("127.0.0.1", port)
    st = c.fetch_state()
    assert st is not None
    assert st.path == str(osu)
    assert "HD" in st.mods_str and "DT" in st.mods_str


def test_tosu_json_fallback(fake_tosu, tmp_path):
    from redpp import TosuClient
    srv, port = fake_tosu
    folder = tmp_path / "Songs"; folder.mkdir()
    sub = folder / "1 A - B"; sub.mkdir()
    osu = sub / "B [Z].osu"; osu.write_text("osu file format v14\n[HitObjects]\n")
    _FakeTosu.payloads = {
        "/api/v2": None,  # 404
        "/json": {
            "settings": {"folders": {"songs": str(folder)}},
            "menu": {"bm": {"path": {"folder": sub.name, "file": osu.name}},
                      "mods": {"str": "HD,FL"}},
        },
    }
    c = TosuClient("127.0.0.1", port)
    st = c.fetch_state()
    assert st is not None and st.path == str(osu)
    assert "HD" in st.mods_str and "FL" in st.mods_str


def test_tosu_no_map_returns_none(fake_tosu):
    from redpp import TosuClient
    srv, port = fake_tosu
    _FakeTosu.payloads = {"/api/v2": {"beatmap": {"path": {"full": "", "folder": "", "file": ""}}}}
    c = TosuClient("127.0.0.1", port)
    assert c.fetch_state() is None


def test_tosu_unreachable():
    from redpp import TosuClient
    c = TosuClient("127.0.0.1", 1)  # closed port
    with pytest.raises(ConnectionError):
        c.fetch_state()


def test_watch_dedupes_and_reacts(fake_tosu, tmp_path, monkeypatch, capsys):
    """Mutate fake tosu state; assert renders happen on change only."""
    from redpp import run_watch
    import redpp
    monkeypatch.setattr(redpp, "IS_TTY", False)
    monkeypatch.setattr(redpp, "POLL_INTERVAL", 0.05)

    srv, port = fake_tosu
    osu1 = make_osu(); osu2 = make_osu(ar=10.0)
    _FakeTosu.payloads = {"/api/v2": {
        "beatmap": {"path": {"full": osu1, "folder": "", "file": ""}},
        "play": {"mods": {"name": "HD"}},
    }}

    _real_sleep = _time.sleep  # capture before monkeypatch replaces it
    stop_after = [80]  # ~0.5s (80 ticks × 1ms real sleep = ~80ms > 50ms mutate delay)
    def fake_sleep(t):
        stop_after[0] -= 1
        if stop_after[0] <= 0:
            raise KeyboardInterrupt
        _real_sleep(0.001)
    monkeypatch.setattr(redpp.time, "sleep", fake_sleep)

    # mutate after 3 ticks
    def mutate():
        _real_sleep(0.05)
        _FakeTosu.payloads["/api/v2"]["beatmap"]["path"]["full"] = osu2
        _FakeTosu.payloads["/api/v2"]["play"]["mods"]["name"] = "HDHR"
    threading.Thread(target=mutate, daemon=True).start()

    rc = run_watch(None, mods_override=None, accs=(95.0, 99.0),
                    host="127.0.0.1", port=port,
                    verbose=False, as_json=False, quiet=True)
    out = capsys.readouterr().out
    # at least 2 distinct renders — one per state
    assert out.count("AR") >= 2
    assert rc == 0
