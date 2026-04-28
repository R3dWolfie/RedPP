"""HeroStrip — top region with bg image, title block, stars, ×/⋮."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import (QPainter, QPixmap, QImage, QLinearGradient, QColor,
                            QBrush, QIcon)
from PySide6.QtWidgets import (QFrame, QLabel, QPushButton, QVBoxLayout,
                                  QHBoxLayout, QGraphicsScene,
                                  QGraphicsPixmapItem, QGraphicsBlurEffect)

_ASSETS = Path(__file__).resolve().parent.parent / "assets"


class HeroStrip(QFrame):
    """Top of the panel. Drag-to-move uses the compositor's native window
    move so it works on both X11 and Wayland — Wayland clients can't
    reposition themselves with QWidget.move()."""
    close_clicked = Signal()
    pin_toggled = Signal()
    revert_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("HeroStrip")
        self.setFixedHeight(160)
        self._bg_pixmap: Optional[QPixmap] = None
        self._setup_ui()

    # ---- public API ---------------------------------------------------
    def set_track(self, *, artist: str, title: str, difficulty: str) -> None:
        self._artist_label.setText(f"[{artist}]" if artist else "")
        self._title_label.setText(title)
        self._diff_label.setText(difficulty)

    def set_pinned(self, pinned: bool) -> None:
        self._pinned_label.setVisible(pinned)
        self._revert_btn.setVisible(pinned)

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
                # Scale to ~2× the strip size keeping the cover aspect, then
                # apply a real Gaussian blur via Qt's graphics effect. Much
                # nicer than the cheap downscale-trick we used before.
                target_w = max(self.width() * 2, 720)
                target_h = max(self.height() * 2, 320)
                scaled = pm.scaled(target_w, target_h,
                                    Qt.KeepAspectRatioByExpanding,
                                    Qt.SmoothTransformation)
                self._bg_pixmap = self._gaussian_blur(scaled, radius=22)
        self.update()

    @staticmethod
    def _gaussian_blur(pm: QPixmap, radius: int = 20) -> QPixmap:
        """Real Gaussian blur via QGraphicsBlurEffect rendered to a pixmap."""
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(pm)
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(radius)
        effect.setBlurHints(QGraphicsBlurEffect.QualityHint)
        item.setGraphicsEffect(effect)
        scene.addItem(item)
        out = QPixmap(pm.size())
        out.fill(Qt.transparent)
        painter = QPainter(out)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        scene.render(painter, QRectF(out.rect()), QRectF(pm.rect()))
        painter.end()
        return out

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
        # Delegate the entire drag to the compositor — works on Wayland
        # (where QWidget.move() is a no-op for frameless toplevels) and
        # on X11 (mapped via _NET_WM_MOVERESIZE).
        if ev.button() == Qt.LeftButton:
            top = self.window()
            wh = top.windowHandle() if top else None
            if wh is not None and wh.startSystemMove():
                ev.accept()
                return
        super().mousePressEvent(ev)

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

        # Override-mode indicator: hidden unless set_pinned(True)
        pin_row = QHBoxLayout(); pin_row.setContentsMargins(0, 0, 0, 0); pin_row.setSpacing(6)
        self._pinned_label = QLabel("[pinned]", self)
        self._pinned_label.setStyleSheet("color: #FFD370; font-size: 9pt;")
        self._pinned_label.hide()
        self._revert_btn = QPushButton("↺", self)
        self._revert_btn.setFixedSize(18, 18)
        self._revert_btn.setStyleSheet(
            "background: transparent; border: none; color: #FFD370; font-size: 12pt;")
        self._revert_btn.setCursor(Qt.PointingHandCursor)
        self._revert_btn.setToolTip("Revert to live mods")
        self._revert_btn.clicked.connect(self.revert_clicked.emit)
        self._revert_btn.hide()
        pin_row.addWidget(self._pinned_label)
        pin_row.addWidget(self._revert_btn)
        pin_row.addStretch(1)
        outer.addLayout(pin_row)

        # bottom: artist / title / diff. Title can wrap to 2 lines for
        # long names; QSS strips opaque backgrounds so the bg image
        # shows through.
        self._artist_label = QLabel("", self); self._artist_label.setObjectName("Artist")
        self._title_label = QLabel("", self); self._title_label.setObjectName("Title")
        self._title_label.setWordWrap(True)
        self._diff_label = QLabel("", self); self._diff_label.setObjectName("Diff")
        outer.addWidget(self._artist_label)
        outer.addWidget(self._title_label)
        outer.addWidget(self._diff_label)
