"""In-play row: shows current pp/acc/combo when labelled, hidden otherwise."""
from typing import Optional
from PySide6.QtWidgets import QLabel


class LiveRow(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("LiveRow")
        self.setText("")
        self.hide()

    def set_content(self, *, label: Optional[str], pp: float, acc: float,
                    combo: int, misses: int) -> None:
        if label is None:
            self.setText("")
            self.hide()
            return
        self.setText(f"{label} {int(pp)}pp · {acc:.2f}% · {combo}x · {misses}m")
        self.show()
