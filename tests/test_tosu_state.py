import json
import pytest
from redpp_app.state import PlayState
from redpp_app.tosu_state import extract_state


def _payload(state: int = 0, hits=None, combo=0, mods_name="HDHR") -> dict:
    p = {
        "client": "lazer",
        "settings": {"folders": {"songs": "/tmp/songs"}},
        "menu": {
            "state": state,
            "bm": {
                "id": 12345,
                "set": 67,
                "md5": "deadbeef",
                "metadata": {
                    "artist": "Test Artist",
                    "title": "Test Title",
                    "difficulty": "Hard",
                },
                "stats": {"AR": 9.0, "OD": 8.0, "CS": 4.0, "HP": 5.0,
                          "BPM": {"common": 180}, "SR": 5.0, "fullSR": 5.0,
                          "maxCombo": 1000},
                "path": {"folder": ".", "file": "h/sh/abcdef",
                         "bg": "b/bg/cafebabe", "full": ""},
            },
            "mods": {"str": mods_name},
        },
        "play": {
            "mods": {"str": mods_name},
            "score": 0,
            "combo": {"current": combo, "max": combo},
            "hits": hits or {"300": 0, "100": 0, "50": 0, "0": 0},
            "accuracy": 100.0,
        },
    }
    return p


def test_extract_idle_when_state_is_song_select():
    # Per osu! state codes: 5 = play-song-select. We treat anything not playing
    # as IDLE so the live row stays hidden.
    s = extract_state(_payload(state=5))
    assert s is not None
    assert s.play_state is PlayState.IDLE
    assert s.path == "/tmp/songs/./h/sh/abcdef"
    assert s.live_mods == "HDHR"
    assert s.title == "Test Title"
    assert s.artist == "Test Artist"
    assert s.difficulty == "Hard"


def test_extract_playing_state():
    s = extract_state(_payload(state=2,
                                hits={"300": 100, "100": 5, "50": 1, "0": 2},
                                combo=300))
    assert s.play_state is PlayState.PLAYING
    assert s.live_play is not None
    assert s.live_play.n300 == 100
    assert s.live_play.n100 == 5
    assert s.live_play.n50 == 1
    assert s.live_play.misses == 2
    assert s.live_play.combo == 300


def test_extract_no_map_returns_none():
    p = _payload()
    p["menu"]["bm"]["path"]["file"] = ""
    p["menu"]["bm"]["path"]["folder"] = ""
    assert extract_state(p) is None


def test_extract_handles_absolute_folder():
    p = _payload()
    p["menu"]["bm"]["path"]["folder"] = "/abs/path/to"
    p["menu"]["bm"]["path"]["file"] = "song.osu"
    s = extract_state(p)
    assert s.path == "/abs/path/to/song.osu"


def test_extract_resolves_bg_path():
    s = extract_state(_payload())
    assert s.bg_path == "/tmp/songs/b/bg/cafebabe"


def test_extract_falls_back_to_play_mods_when_menu_empty():
    p = _payload()
    p["menu"]["mods"] = {"str": ""}
    p["play"]["mods"] = {"str": "DTHD"}
    s = extract_state(p)
    assert s.live_mods == "DTHD"


def test_extract_handles_array_mods_form():
    p = _payload()
    p["menu"]["mods"] = {"array": [{"acronym": "HD"}, {"acronym": "FL"}]}
    s = extract_state(p)
    assert s.live_mods == "HDFL"


def test_extract_lazer_client_sets_lazer_true():
    """Default tosu payload reports client=lazer → state.lazer=True."""
    s = extract_state(_payload())
    assert s.lazer is True


def test_extract_stable_client_sets_lazer_false():
    """When tosu reports stable, the pp algorithm flag flips."""
    p = _payload()
    p["client"] = "stable"
    s = extract_state(p)
    assert s.lazer is False


def test_extract_missing_client_defaults_to_lazer():
    """Older tosu builds may omit the client field — default to lazer."""
    p = _payload()
    p.pop("client", None)
    s = extract_state(p)
    assert s.lazer is True
