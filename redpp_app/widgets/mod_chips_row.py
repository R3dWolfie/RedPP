"""Two rows of mod chips covering the pp-relevant osu!std mods.

Row 1 (difficulty up):    HD HR DT FL
Row 2 (difficulty mods):  EZ HT NC BL

Owns the AppState reference; clicks update state.override_mods through
state.toggle_mod() and re-render visual state.
"""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

from .mod_chip import ModChip
from ..state import AppState

CHIP_ROWS: tuple[tuple[str, ...], ...] = (
    ("HD", "HR", "DT", "FL"),
    ("EZ", "HT", "NC", "BL"),
)
CHIP_ORDER: tuple[str, ...] = tuple(m for row in CHIP_ROWS for m in row)


class ModChipsRow(QFrame):
    state_changed = Signal()  # emitted whenever effective mods change

    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state
        self._chips: list[ModChip] = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)
        outer.setSpacing(4)
        for row in CHIP_ROWS:
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            row_layout.addStretch(1)
            for acr in row:
                c = ModChip(acr, self)
                c.toggled_chip.connect(self._on_chip_toggle)
                self._chips.append(c)
                row_layout.addWidget(c)
            row_layout.addStretch(1)
            outer.addLayout(row_layout)
        self._sync_from_state()

    def chips(self) -> list[ModChip]:
        return list(self._chips)

    def revert_override(self) -> None:
        self._state.revert_override()
        self._sync_from_state()
        self.state_changed.emit()

    def update_live_mods(self, live_mods: str) -> None:
        self._state.live_mods = live_mods
        if not self._state.is_overriding():
            self._sync_from_state()
            self.state_changed.emit()

    def _on_chip_toggle(self, acronym: str) -> None:
        self._state.toggle_mod(acronym)
        self._sync_from_state()
        self.state_changed.emit()

    def _sync_from_state(self) -> None:
        active = set()
        eff = self._state.effective_mods()
        for i in range(0, len(eff), 2):
            active.add(eff[i:i+2].upper())
        for c in self._chips:
            c.set_active(c.acronym in active)
