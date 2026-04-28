"""PP result row: rank badge + big number.

Rank is derived from accuracy per osu!lazer's grade thresholds:
  100%  → SS   (gold)
  95%+  → S    (cyan)
  90%+  → A    (lime)
  80%+  → B    (blue)
  70%+  → C    (purple)
  <70%  → D    (red)

The badge is painted procedurally so we don't need 6 SVG files.
"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


def format_pp(pp: float) -> str:
    """Compact pp display: comma-grouped for 4–5 digit values, K/M
    suffix for the absurd Aspire-tier numbers that would otherwise blow
    past the panel width."""
    if pp >= 1_000_000:
        return f"{pp / 1_000_000:.1f}M"
    if pp >= 100_000:
        return f"{pp / 1_000:.0f}K"
    if pp >= 10_000:
        return f"{pp:,.0f}"
    return f"{pp:.0f}"


def compute_rank(accuracy: float) -> str:
    """Return 'SS' | 'S' | 'A' | 'B' | 'C' | 'D' for an accuracy 0-100."""
    if accuracy >= 100.0:
        return "SS"
    if accuracy >= 95.0:
        return "S"
    if accuracy >= 90.0:
        return "A"
    if accuracy >= 80.0:
        return "B"
    if accuracy >= 70.0:
        return "C"
    return "D"


_RANK_COLORS = {
    "SS": "#FFD370",   # gold
    "S":  "#5BD7E0",   # cyan
    "A":  "#88C540",   # lime
    "B":  "#5DADE2",   # blue
    "C":  "#B47BC9",   # purple
    "D":  "#E74C3C",   # red
}


def make_rank_pixmap(rank: str, size: int = 64) -> QPixmap:
    """Paint a rounded-square badge with the rank letter centered."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    color = QColor(_RANK_COLORS.get(rank, _RANK_COLORS["D"]))
    p.setPen(QPen(color, 0))
    p.setBrush(QBrush(color))
    pad = max(2, size // 32)
    p.drawRoundedRect(pad, pad, size - 2 * pad, size - 2 * pad,
                       size // 4, size // 4)
    f = QFont("Arial")
    f.setBold(True)
    f.setPointSize(int(size * 0.55) if len(rank) == 1 else int(size * 0.42))
    p.setFont(f)
    p.setPen(QColor("#0E1622"))
    p.drawText(pm.rect(), Qt.AlignCenter, rank)
    p.end()
    return pm


class PPResult(QFrame):
    BADGE_PX = 44

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(10)
        self._badge = QLabel(self)
        self._badge.setFixedSize(QSize(self.BADGE_PX, self.BADGE_PX))
        self._badge.setPixmap(make_rank_pixmap("D", self.BADGE_PX))
        self._label = QLabel("0pp for 0.0%", self)
        self._label.setObjectName("PPNumber")
        layout.addWidget(self._badge)
        layout.addWidget(self._label, 1)

    def set_pp(self, pp: float, accuracy: float) -> None:
        rank = compute_rank(accuracy)
        self._badge.setPixmap(make_rank_pixmap(rank, self.BADGE_PX))
        self._label.setText(f"{format_pp(pp)}pp for {accuracy:.1f}%")
