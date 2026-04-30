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


def test_compute_render_threads_lazer_flag(monkeypatch):
    """state.lazer must reach the underlying redpp.ParsedScore.

    We don't compare numeric pp values here — synthetic maps are too
    simple to show the algorithmic difference reliably. Instead we
    intercept redpp.calc_one and assert what was passed in."""
    import redpp
    p = make_osu()
    captured = []

    def fake_calc_one(path, score):
        captured.append(score.lazer)
        # Return a real RenderData by calling the original implementation
        # so compute_render still returns something usable.
        return real_calc_one(path, score)
    real_calc_one = redpp.calc_one
    monkeypatch.setattr(redpp, "calc_one", fake_calc_one)

    compute_render(AppState(path=p, slider_acc=99.0, lazer=True))
    compute_render(AppState(path=p, slider_acc=99.0, lazer=False))
    assert captured == [True, False]


def test_compute_live_pp_threads_lazer_flag(monkeypatch):
    """Same plumbing check for the in-play path."""
    import redpp
    from redpp_app.calc import compute_live_pp
    p = make_osu()
    captured = []
    real_calc_one = redpp.calc_one
    def fake(path, score):
        captured.append(score.lazer)
        return real_calc_one(path, score)
    monkeypatch.setattr(redpp, "calc_one", fake)

    state = AppState(path=p, lazer=False, play_state=PlayState.PLAYING,
                     live_play=LivePlay(n300=80, n100=5, n50=1, misses=2,
                                          combo=200, accuracy=97.5))
    compute_live_pp(state)
    assert captured == [False]
