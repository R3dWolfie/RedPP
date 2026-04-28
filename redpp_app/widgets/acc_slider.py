"""Yellow track + white knob accuracy slider, 0.1% step."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QSlider, QLabel


class AccSlider(QFrame):
    acc_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(2)
        self._label = QLabel("Accuracy: 100.0%", self); self._label.setObjectName("AccLabel")
        self._slider = QSlider(Qt.Horizontal, self)
        self._min = 90.0; self._max = 100.0; self._step = 0.1
        self._configure_slider()
        self._slider.valueChanged.connect(self._on_changed)
        layout.addWidget(self._label)
        layout.addWidget(self._slider)
        self._slider.setValue(self._slider.maximum())  # default 100%

    def _configure_slider(self) -> None:
        ticks = round((self._max - self._min) / self._step)
        self._slider.setMinimum(0); self._slider.setMaximum(ticks)

    def set_range(self, min_: float, max_: float) -> None:
        self._min = min_; self._max = max_
        self._configure_slider()
        self._slider.setValue(self._slider.maximum())

    def set_value(self, acc: float) -> None:
        ticks = round((acc - self._min) / self._step)
        ticks = max(0, min(ticks, self._slider.maximum()))
        self._slider.setValue(ticks)

    def value(self) -> float:
        return self._min + self._slider.value() * self._step

    def _on_changed(self, _) -> None:
        v = self.value()
        self._label.setText(f"Accuracy: {v:.1f}%")
        self.acc_changed.emit(v)
