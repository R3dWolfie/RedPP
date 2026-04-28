"""One-line `AR x.x · OD x.x · CS x.x · HP x.x · BPM nnn`."""
from PySide6.QtWidgets import QLabel


class StatsLine(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("StatsLine")
        self.setText("")

    def set_stats(self, *, ar: float, od: float, cs: float, hp: float, bpm: int) -> None:
        self.setText(f"AR {ar:.1f} · OD {od:.1f} · CS {cs:.1f} · HP {hp:.1f} · BPM {bpm}")
