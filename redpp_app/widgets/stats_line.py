"""One-line `AR: x.xx OD: x.xx CS: x.xx HP: x.xx BPM: nnn`."""
from PySide6.QtWidgets import QLabel


class StatsLine(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("StatsLine")
        self.setText("")

    def set_stats(self, *, ar: float, od: float, cs: float, hp: float, bpm: int) -> None:
        self.setText(f"AR: {ar:.2f}  OD: {od:.2f}  CS: {cs:.2f}  HP: {hp:.2f}  BPM: {bpm}")
