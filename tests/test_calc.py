import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from redpp_app.state import AppState, PlayState, LivePlay
from redpp_app.calc import compute_render
from test_redpp import make_osu  # reuse synthetic .osu builder from CLI tests


def test_compute_render_basic_slider():
    p = make_osu()
    state = AppState(path=p, slider_acc=99.0)
    rd = compute_render(state)
    assert rd.pp > 0
    assert rd.accuracy == pytest.approx(99.0)
    assert rd.stars > 0


def test_compute_render_uses_effective_mods():
    p = make_osu(ar=9.0)
    nm = compute_render(AppState(path=p, slider_acc=100.0))
    hr = compute_render(AppState(path=p, slider_acc=100.0, override_mods="HR"))
    assert hr.ar > nm.ar
    assert hr.pp > nm.pp


def test_compute_live_pp_uses_hit_counts():
    from redpp_app.calc import compute_live_pp
    p = make_osu()
    state = AppState(path=p, play_state=PlayState.PLAYING, live_play=LivePlay(
        n300=80, n100=5, n50=1, misses=2, combo=200, accuracy=97.5))
    pp = compute_live_pp(state)
    assert pp > 0


def test_compute_render_returns_none_for_no_path():
    state = AppState(path=None)
    assert compute_render(state) is None
