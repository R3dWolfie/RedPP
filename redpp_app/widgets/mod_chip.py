"""Hexagonal toggle button for one mod (HD/HR/DT/FL)."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QSize, QPointF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPolygonF
from PySide6.QtWidgets import QPushButton

_ACTIVE_FILL = QColor("#FFD370")
_ACTIVE_BORDER = QColor("#FFD370")
_INACTIVE_FILL = QColor(0, 0, 0, 0)            # transparent
_INACTIVE_BORDER = QColor(255, 211, 112, 90)   # dim gold
_ACTIVE_TEXT = QColor("#0E1622")
_INACTIVE_TEXT = QColor(255, 211, 112, 130)    # dim gold


class ModChip(QPushButton):
    """Stateful hex chip for a single 2-letter mod acronym."""

    toggled_chip = Signal(str)  # emits the acronym when clicked

    def __init__(self, acronym: str, parent=None) -> None:
        super().__init__(parent)
        self._acronym = acronym.upper()
        self._active = False
        self.setFixedSize(QSize(48, 48))
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(lambda: self.toggled_chip.emit(self._acronym))

    @property
    def acronym(self) -> str:
        return self._acronym

    @property
    def active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        if self._active != active:
            self._active = active
            self.update()

    # ---- painting ----------------------------------------------------
    def _hexagon(self) -> QPolygonF:
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) / 2.0 - 2  # leave 2px padding so border doesn't clip
        # Pointy-top hexagon
        pts = [QPointF(cx, cy - r),
               QPointF(cx + r * 0.866, cy - r * 0.5),
               QPointF(cx + r * 0.866, cy + r * 0.5),
               QPointF(cx, cy + r),
               QPointF(cx - r * 0.866, cy + r * 0.5),
               QPointF(cx - r * 0.866, cy - r * 0.5)]
        return QPolygonF(pts)

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        fill = _ACTIVE_FILL if self._active else _INACTIVE_FILL
        border = _ACTIVE_BORDER if self._active else _INACTIVE_BORDER
        text = _ACTIVE_TEXT if self._active else _INACTIVE_TEXT
        p.setPen(QPen(border, 2))
        p.setBrush(QBrush(fill))
        p.drawPolygon(self._hexagon())
        # Acronym
        f = QFont(self.font())
        f.setBold(True); f.setPointSize(10)
        p.setFont(f); p.setPen(text)
        p.drawText(self.rect(), Qt.AlignCenter, self._acronym)
        p.end()
