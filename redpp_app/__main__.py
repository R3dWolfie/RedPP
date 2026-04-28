"""Entry point: `python -m redpp_app`."""
from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication

from .main_window import RedPPMainWindow


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv or sys.argv)
    app.setApplicationName("RedPP")
    w = RedPPMainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
