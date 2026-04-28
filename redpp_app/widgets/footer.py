"""'RedPP vX.Y.Z' footer."""
from PySide6.QtWidgets import QLabel


class Footer(QLabel):
    def __init__(self, version: str, parent=None) -> None:
        super().__init__(f"RedPP v{version}", parent)
        self.setObjectName("Footer")
