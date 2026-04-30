"""Row of 4 numeric inputs below the slider: Combo · 100s · 50s · Misses.

These let the user dial in a specific score state (e.g. 500 combo + 0
miss = sliderbreak). Slider still drives the target accuracy; rosu-pp
fills in n300 to match. When all inputs are at default, the calc behaves
exactly like before (FC at slider's %).
"""
from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QSpinBox


class HitInputs(QFrame):
    # emitted whenever any field changes — payload is (combo|None, n100, n50, misses)
    state_changed = Signal(object, int, int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._max_combo = 0
        self._building = False  # suppress signal storms during programmatic updates

        grid = QGridLayout(self)
        grid.setContentsMargins(12, 0, 12, 4)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(0)

        self._combo  = self._make_box(grid, 0, "Combo", 0, 999_999)
        self._n100   = self._make_box(grid, 1, "100s",  0, 999_999)
        self._n50    = self._make_box(grid, 2, "50s",   0, 999_999)
        self._miss   = self._make_box(grid, 3, "Miss",  0, 999_999)

        for spin in (self._combo, self._n100, self._n50, self._miss):
            spin.valueChanged.connect(self._emit)

    def _make_box(self, grid: QGridLayout, col: int, label: str,
                   lo: int, hi: int) -> QSpinBox:
        lbl = QLabel(label, self)
        lbl.setObjectName("HitLabel")
        lbl.setAlignment(Qt.AlignCenter)
        spin = QSpinBox(self)
        spin.setObjectName("HitSpin")
        spin.setRange(lo, hi)
        spin.setButtonSymbols(QSpinBox.NoButtons)
        spin.setAlignment(Qt.AlignCenter)
        spin.setFixedHeight(22)
        grid.addWidget(lbl,  0, col)
        grid.addWidget(spin, 1, col)
        return spin

    # -------- public API --------
    def set_max_combo(self, max_combo: int) -> None:
        """Called when the map changes. Updates the combo upper bound and
        resets the displayed combo to the new max if the user hadn't
        typed an explicit value."""
        self._max_combo = max_combo
        self._building = True
        try:
            self._combo.setRange(0, max(max_combo, 1))
            # If the user hadn't customized combo, snap to the new max.
            if self._combo.value() == 0 or self._combo.value() == self._max_combo:
                self._combo.setValue(max_combo)
        finally:
            self._building = False

    def reset(self) -> None:
        """Clear all fields back to FC defaults (combo = max, others = 0)."""
        self._building = True
        try:
            self._combo.setValue(self._max_combo)
            self._n100.setValue(0)
            self._n50.setValue(0)
            self._miss.setValue(0)
        finally:
            self._building = False
        self._emit()

    def values(self) -> tuple[Optional[int], int, int, int]:
        """Return (combo|None, n100, n50, misses) where combo=None means
        'FC' (i.e. the user hasn't customized it — value matches max)."""
        combo: Optional[int] = self._combo.value()
        if combo == self._max_combo:
            combo = None  # treat 'at max' as the FC default
        return combo, self._n100.value(), self._n50.value(), self._miss.value()

    # -------- internals --------
    def _emit(self) -> None:
        if self._building:
            return
        self.state_changed.emit(*self.values())
