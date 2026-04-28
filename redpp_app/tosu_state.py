"""Pure function: tosu /json payload -> AppState fragment.

Kept stateless and Qt-free so it's easy to unit-test.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

from .state import AppState, LivePlay, PlayState


# Per osu! protocol: 2 = playing, 7 = ranking, etc. Watching a replay or
# spectating reuses 2 with extra flags; tosu may not expose them distinctly,
# so we treat 2 as PLAYING and let SPECTATING/REPLAY be inferred when other
# fields surface (see _infer_play_state). For now, only PLAYING is observable.
_OSU_STATE_PLAYING = 2


def _extract_mods_str(mods_obj: dict | None) -> str:
    if not mods_obj:
        return ""
    if isinstance(mods_obj.get("array"), list):
        joined = "".join(m.get("acronym", "") for m in mods_obj["array"]
                         if isinstance(m, dict))
        if joined:
            return joined.upper()
    for k in ("str", "name", "acronym"):
        v = mods_obj.get(k)
        if v:
            return "".join(re.findall(r"[A-Za-z]{2}", v)).upper()
    return ""


def _resolve_path(songs: str, folder: str, file_: str) -> Optional[str]:
    if not (folder and file_):
        return None
    if Path(folder).is_absolute():
        return folder.rstrip("/") + "/" + file_
    if not songs:
        return None
    return songs.rstrip("/") + "/" + folder + "/" + file_


def _infer_play_state(menu_state: int, replay_flag: bool, spectator_flag: bool) -> PlayState:
    if menu_state != _OSU_STATE_PLAYING:
        return PlayState.IDLE
    if replay_flag:
        return PlayState.REPLAY
    if spectator_flag:
        return PlayState.SPECTATING
    return PlayState.PLAYING


def extract_state(payload: dict) -> Optional[AppState]:
    menu = payload.get("menu") or {}
    bm = menu.get("bm") or {}
    settings = payload.get("settings") or {}
    folders = settings.get("folders") or {}
    songs = folders.get("songs") or ""
    pobj = bm.get("path") or {}
    path = _resolve_path(songs, pobj.get("folder") or "", pobj.get("file") or "")
    if path is None:
        return None

    bg_rel = pobj.get("bg") or ""
    # bg is relative to the songs root directly (not to the map's subfolder).
    bg_path = (songs.rstrip("/") + "/" + bg_rel) if (bg_rel and songs) else None

    # mods: prefer menu, fall back to play
    live_mods = _extract_mods_str(menu.get("mods")) or _extract_mods_str((payload.get("play") or {}).get("mods"))

    md = bm.get("metadata") or {}
    stats = bm.get("stats") or {}

    play = payload.get("play") or {}
    state_int = int(menu.get("state") or 0)
    # tosu doesn't (yet) emit a clean spectator/replay flag, so for now we only
    # ever produce IDLE or PLAYING here. The poller can promote to SPECTATING
    # or REPLAY based on additional signals (e.g. menu.gameMode bits) in a
    # later iteration.
    play_state = _infer_play_state(state_int, replay_flag=False, spectator_flag=False)

    live_play: Optional[LivePlay] = None
    if play_state is PlayState.PLAYING:
        hits = play.get("hits") or {}
        combo_obj = play.get("combo") or {}
        live_play = LivePlay(
            n300=int(hits.get("300", 0)),
            n100=int(hits.get("100", 0)),
            n50=int(hits.get("50", 0)),
            misses=int(hits.get("0", 0)),
            combo=int(combo_obj.get("current", 0)),
            accuracy=float(play.get("accuracy", 100.0)),
        )

    return AppState(
        path=path,
        live_mods=live_mods,
        play_state=play_state,
        live_play=live_play,
        title=md.get("title", ""),
        artist=md.get("artist", ""),
        difficulty=md.get("difficulty", ""),
        set_id=int(bm.get("set", 0)),
        bg_path=bg_path,
        base_stars=float(stats.get("SR", 0.0)),
        mod_stars=float(stats.get("fullSR", stats.get("SR", 0.0))),
    )
