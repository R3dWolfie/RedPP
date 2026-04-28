"""HeroStrip — top 140px region with bg image, title block, stars, ×/⋮."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal, QPoint, QRectF
from PySide6.QtGui import (QPainter, QPixmap, QImage, QLinearGradient, QColor,
                            QBrush, QIcon)
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget

_ASSETS = Path(__file__).resolve().parent.parent / "assets"


class HeroStrip(QFrame):
    drag_delta = Signal(int, int)        # dx, dy in window coords
    close_clicked = Signal()
    pin_toggled = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("HeroStrip")
        self.setFixedHeight(140)
        self._bg_pixmap: Optional[QPixmap] = None
        self._press_pos: Optional[QPoint] = None
        self._setup_ui()

    # ---- public API ---------------------------------------------------
    def set_track(self, *, artist: str, title: str, difficulty: str) -> None:
        self._artist_label.setText(f"[{artist}]" if artist else "")
        self._title_label.setText(title)
        self._diff_label.setText(difficulty)

    def set_stars(self, *, base: float, mod: float) -> None:
        self._stars_label.setText(f"{mod:.2f}")
        self._chevron.setVisible(mod > base + 0.05)

    def set_background(self, image_path: Optional[str]) -> None:
        if not image_path or not Path(image_path).is_file():
            self._bg_pixmap = None
        else:
            pm = QPixmap(image_path)
            if pm.isNull():
                self._bg_pixmap = None
            else:
                # Crop-cover into the strip's aspect ratio, then blur via QImage.
                self._bg_pixmap = self._blur(pm.scaled(
                    self.width() * 2, 280, Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation))
        self.update()

    @staticmethod
    def _blur(pm: QPixmap, radius: int = 12) -> QPixmap:
        # Cheap stack-blur by repeated downscale/upscale; keeps stdlib-only.
        img = pm.toImage()
        small = img.scaled(img.width() // (radius // 2 + 1),
                            img.height() // (radius // 2 + 1),
                            Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        return QPixmap.fromImage(small.scaled(img.width(), img.height(),
                                                Qt.IgnoreAspectRatio,
                                                Qt.SmoothTransformation))

    # ---- painting -----------------------------------------------------
    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        if self._bg_pixmap is not None:
            p.drawPixmap(rect, self._bg_pixmap)
        else:
            grad = QLinearGradient(0, 0, 0, rect.height())
            grad.setColorAt(0.0, QColor("#1F2A3D"))
            grad.setColorAt(1.0, QColor("#0E1622"))
            p.fillRect(rect, QBrush(grad))
        # dim overlay
        p.fillRect(rect, QColor(0, 0, 0, 115))
        p.end()
        super().paintEvent(_ev)

    # ---- drag ---------------------------------------------------------
    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.LeftButton:
            self._press_pos = ev.position().toPoint()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev) -> None:
        if self._press_pos is not None and (ev.buttons() & Qt.LeftButton):
            now = ev.position().toPoint()
            d = now - self._press_pos
            self.drag_delta.emit(d.x(), d.y())
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev) -> None:
        self._press_pos = None
        super().mouseReleaseEvent(ev)

    # ---- layout -------------------------------------------------------
    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 8, 12)
        outer.setSpacing(0)

        # top row: stars (left expand), buttons right
        top = QHBoxLayout(); top.setContentsMargins(0, 0, 0, 0); top.setSpacing(4)
        self._chevron = QLabel(self)
        self._chevron.setPixmap(QIcon(str(_ASSETS / "chevron_up.svg")).pixmap(18, 18))
        self._chevron.setVisible(False)
        self._stars_label = QLabel("0.00", self); self._stars_label.setObjectName("Stars")

        top.addStretch(1)
        top.addWidget(self._stars_label)
        top.addWidget(self._chevron)
        top.addSpacing(6)
        self._pin_btn = QPushButton("⋮", self); self._pin_btn.setObjectName("Pin")
        self._pin_btn.setFixedSize(20, 20)
        self._pin_btn.setCursor(Qt.PointingHandCursor)
        self._pin_btn.clicked.connect(self.pin_toggled.emit)
        top.addWidget(self._pin_btn)
        self._close_btn = QPushButton("×", self); self._close_btn.setObjectName("Close")
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.clicked.connect(self.close_clicked.emit)
        top.addWidget(self._close_btn)
        outer.addLayout(top)

        outer.addStretch(1)

        # bottom: artist / title / diff
        self._artist_label = QLabel("", self); self._artist_label.setObjectName("Artist")
        self._title_label = QLabel("", self); self._title_label.setObjectName("Title")
        self._diff_label = QLabel("", self); self._diff_label.setObjectName("Diff")
        outer.addWidget(self._artist_label)
        outer.addWidget(self._title_label)
        outer.addWidget(self._diff_label)
