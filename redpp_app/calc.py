"""Bridges AppState -> redpp.calc_one (RenderData) for the UI to consume."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
import redpp  # noqa: E402

from .state import AppState, PlayState


def compute_render(state: AppState):
    """Slider-driven what-if pp.

    Returns RenderData or None when the path is missing or the map is
    suspicious."""
    if not state.path:
        return None
    score = redpp.ParsedScore(
        mods=state.effective_mods(),
        accuracy=state.slider_acc,
        lazer=state.lazer,
    )
    try:
        return redpp.calc_one(state.path, score)
    except (FileNotFoundError, RuntimeError):
        return None


def compute_live_pp(state: AppState) -> float:
    """In-play pp from the player's current hit counts. 0.0 if no live data."""
    if state.play_state is PlayState.IDLE or state.live_play is None or not state.path:
        return 0.0
    lp = state.live_play
    score = redpp.ParsedScore(
        mods=state.live_mods,         # always live mods, not override
        n300=lp.n300, n100=lp.n100, n50=lp.n50, misses=lp.misses,
        combo=lp.combo, lazer=state.lazer,
    )
    try:
        rd = redpp.calc_one(state.path, score)
    except (FileNotFoundError, RuntimeError):
        return 0.0
    return rd.pp
