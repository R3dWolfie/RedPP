"""Single source of truth for the panel's UI state.

Pure data + a few helpers. No Qt imports — keeps the state testable and
re-usable from anywhere.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class PlayState(Enum):
    IDLE = auto()        # menu, song select, results — slider primary, no live row
    PLAYING = auto()     # user playing — live row labeled "Now:"
    SPECTATING = auto()  # user spectating — live row labeled "Spectating:"
    REPLAY = auto()      # watching replay — live row labeled "Replay:"


def _split_mods(mods: str) -> list[str]:
    """'HDHR' -> ['HD','HR']."""
    return [mods[i:i+2].upper() for i in range(0, len(mods), 2)]


def _join_mods(mods: list[str]) -> str:
    return "".join(mods)


@dataclass
class LivePlay:
    """Hit counts + combo from an in-progress play. Drives the live row."""
    n300: int = 0
    n100: int = 0
    n50: int = 0
    misses: int = 0
    combo: int = 0
    accuracy: float = 100.0
    pp: float = 0.0


@dataclass
class AppState:
    path: Optional[str] = None              # absolute path to the .osu file
    live_mods: str = ""                     # mods reported by tosu
    override_mods: Optional[str] = None     # user-pinned, takes precedence
    slider_acc: float = 100.0
    play_state: PlayState = PlayState.IDLE
    live_play: Optional[LivePlay] = None    # populated when play_state != IDLE
    lazer: bool = True                      # tosu reports client=lazer|stable;
                                             # flips the pp algorithm accordingly

    # User-typed score state for the "what-if with these specific hits"
    # row below the slider. None / 0 means "use slider's FC-at-X% default".
    score_combo: Optional[int] = None       # None = FC (max combo of map)
    score_n100: int = 0
    score_n50: int = 0
    score_misses: int = 0

    # Map metadata for header rendering (filled by the renderer, not the poller)
    title: str = ""
    artist: str = ""
    difficulty: str = ""
    set_id: int = 0
    bg_path: Optional[str] = None
    base_stars: float = 0.0
    mod_stars: float = 0.0

    def is_overriding(self) -> bool:
        return self.override_mods is not None

    def effective_mods(self) -> str:
        return self.override_mods if self.override_mods is not None else self.live_mods

    def revert_override(self) -> None:
        self.override_mods = None

    def toggle_mod(self, mod: str) -> None:
        """First touch enters override mode (seeded with current live mods).
        Subsequent toggles add/remove from the override."""
        mod = mod.upper()
        base = self.override_mods if self.override_mods is not None else self.live_mods
        active = _split_mods(base)
        if mod in active:
            active.remove(mod)
        else:
            active.append(mod)
        new_override = _join_mods(active)
        # Auto-revert when override now equals live (set-wise, order-independent).
        live_set = set(_split_mods(self.live_mods))
        new_set = set(_split_mods(new_override))
        if new_set == live_set:
            self.override_mods = None
        else:
            self.override_mods = new_override

    def live_row_label(self) -> Optional[str]:
        return {
            PlayState.IDLE: None,
            PlayState.PLAYING: "Now:",
            PlayState.SPECTATING: "Spectating:",
            PlayState.REPLAY: "Replay:",
        }[self.play_state]

    def dedupe_key(self) -> tuple:
        """Anything that should trigger a full preset re-render."""
        return (self.path, self.effective_mods(), round(self.slider_acc, 2),
                self.play_state)
