import pytest
from redpp_app.state import AppState, PlayState


def test_default_state_is_idle_no_override():
    s = AppState()
    assert s.path is None
    assert s.live_mods == ""
    assert s.override_mods is None
    assert s.is_overriding() is False
    assert s.effective_mods() == ""
    assert s.slider_acc == 100.0
    assert s.play_state is PlayState.IDLE


def test_override_takes_precedence_over_live_mods():
    s = AppState(live_mods="HD", override_mods="HDHR")
    assert s.is_overriding() is True
    assert s.effective_mods() == "HDHR"


def test_revert_override_returns_to_live():
    s = AppState(live_mods="HD", override_mods="HDHR")
    s.revert_override()
    assert s.is_overriding() is False
    assert s.effective_mods() == "HD"


def test_toggle_mod_sets_override():
    s = AppState(live_mods="HD")
    s.toggle_mod("HR")
    assert s.is_overriding() is True
    assert "HR" in s.effective_mods()
    assert "HD" in s.effective_mods()


def test_toggle_mod_auto_reverts_when_override_matches_live():
    """When the user toggles back to the live state, override clears
    automatically — otherwise there's no way out of override mode without
    a UI button."""
    s = AppState(live_mods="HD")
    s.toggle_mod("HR")        # override = "HDHR"
    assert s.is_overriding() is True
    s.toggle_mod("HR")        # override = "HD" → matches live → revert
    assert s.is_overriding() is False
    assert s.effective_mods() == "HD"


def test_auto_revert_set_compare_ignores_order():
    """Auto-revert should compare mod sets, not strings — so HDHR vs HRHD
    still revert when they're the same set."""
    s = AppState(live_mods="HRHD")  # weird order
    s.toggle_mod("DT")        # override = "HRHDDT"
    s.toggle_mod("DT")        # override = "HRHD" → matches live → revert
    assert s.is_overriding() is False


def test_play_state_label_matches_state():
    assert AppState(play_state=PlayState.IDLE).live_row_label() is None
    assert AppState(play_state=PlayState.PLAYING).live_row_label() == "Now:"
    assert AppState(play_state=PlayState.SPECTATING).live_row_label() == "Spectating:"
    assert AppState(play_state=PlayState.REPLAY).live_row_label() == "Replay:"


def test_dedupe_key_changes_when_relevant_fields_change():
    s = AppState(path="/tmp/a.osu", live_mods="HD", slider_acc=99.0)
    k1 = s.dedupe_key()
    s.slider_acc = 99.1
    assert s.dedupe_key() != k1


def test_setting_live_mods_does_not_clear_override():
    """Spec: switching maps preserves the override pin."""
    s = AppState(live_mods="HD", override_mods="HDHR")
    s.live_mods = "DT"
    assert s.is_overriding() is True
    assert s.effective_mods() == "HDHR"
