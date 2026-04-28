"""PP result row: cyan S badge + big number."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

_ASSETS = Path(__file__).resolve().parent.parent / "assets"


class PPResult(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(10)
        self._badge = QLabel(self)
        self._badge.setPixmap(QPixmap(str(_ASSETS / "s_rank.svg"))
                               .scaledToHeight(40, Qt.SmoothTransformation))
        self._label = QLabel("0pp for 0.0%", self)
        self._label.setObjectName("PPNumber")
        layout.addWidget(self._badge)
        layout.addWidget(self._label, 1)

    def set_pp(self, pp: float, accuracy: float) -> None:
        self._label.setText(f"{pp:.0f}pp for {accuracy:.1f}%")
