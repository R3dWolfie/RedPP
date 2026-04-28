import json
import re
import pytest
from redpp import parse_score_string, ParsedScore

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
