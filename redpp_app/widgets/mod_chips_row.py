"""Row of 4 mod chips: HD, HR, DT, FL.

Owns the AppState reference; clicks update state.override_mods through
state.toggle_mod() and re-render visual state."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout

from .mod_chip import ModChip
from ..state import AppState

CHIP_ORDER = ("HD", "HR", "DT", "FL")


class ModChipsRow(QFrame):
    state_changed = Signal()  # emitted whenever effective mods change

    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self._state = state
        self._chips: list[ModChip] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addStretch(1)
        for acr in CHIP_ORDER:
            c = ModChip(acr, self)
            c.toggled_chip.connect(self._on_chip_toggle)
            self._chips.append(c)
            layout.addWidget(c)
        layout.addStretch(1)
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
