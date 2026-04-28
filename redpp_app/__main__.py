"""Entry point: `python -m redpp_app`."""
from __future__ import annotations
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget


class _Skeleton(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(280, 420)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setStyleSheet("background:#1A2333; border-radius:8px;")


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv or sys.argv)
    w = _Skeleton()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
