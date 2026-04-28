"""Main panel — composes all widgets and wires signals."""
from __future__ import annotations
import json
import os
from pathlib import Path
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QAction, QActionGroup
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                  QPushButton, QMenu)

from . import __version__
from .state import AppState, PlayState
from .poller import TosuPoller
from .calc import compute_render, compute_live_pp
from .widgets.hero_strip import HeroStrip
from .widgets.mod_chips_row import ModChipsRow
from .widgets.stats_line import StatsLine
from .widgets.pp_result import PPResult
from .widgets.acc_slider import AccSlider
from .widgets.live_row import LiveRow
from .widgets.footer import Footer

_ASSETS = Path(__file__).resolve().parent / "assets"


def _state_file() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME",
                                     str(Path.home() / ".config")))
    return base / "redpp" / "state.json"


def _load_persisted() -> dict:
    f = _state_file()
    if f.is_file():
        try:
            return json.loads(f.read_text())
        except Exception:
            return {}
    return {}


def _save_persisted(d: dict) -> None:
    f = _state_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d))


class RedPPMainWindow(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(280, 420)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self._state = AppState()
        self._show_live_row_enabled = True
        self._acc_range = (90.0, 100.0)
        self._build_ui()
        self._restore_persisted()
        self._start_poller()
        self._drag_origin: QPoint | None = None

    # ---- ui -----------------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        self._hero = HeroStrip(self)
        self._hero.drag_delta.connect(self._on_drag)
        self._hero.close_clicked.connect(self.close)
        self._hero.pin_toggled.connect(self._show_settings_menu)
        outer.addWidget(self._hero)

        self._chips = ModChipsRow(self._state, self)
        self._chips.state_changed.connect(self._recalc)
        outer.addWidget(self._chips)

        self._hero.revert_clicked.connect(self._chips.revert_override)

        self._stats = StatsLine(self)
        outer.addWidget(self._stats)

        self._pp = PPResult(self)
        outer.addWidget(self._pp)

        self._slider = AccSlider(self)
        self._slider.acc_changed.connect(self._on_slider)
        outer.addWidget(self._slider)

        self._live = LiveRow(self)
        outer.addWidget(self._live)

        outer.addStretch(1)
        outer.addWidget(Footer(__version__, self))

        # apply theme
        qss = (_ASSETS.parent / "theme.qss").read_text()
        self.setStyleSheet(qss)

    # ---- poller -------------------------------------------------------
    def _start_poller(self) -> None:
        self._poller = TosuPoller()
        self._poller.state_changed.connect(self._on_tosu_state)
        self._poller.start()

    def _on_tosu_state(self, st) -> None:
        # AppState fragment from extractor: copy what we want into our state
        self._state.path = st.path
        self._state.live_play = st.live_play
        self._state.play_state = st.play_state
        self._state.title = st.title
        self._state.artist = st.artist
        self._state.difficulty = st.difficulty
        self._state.set_id = st.set_id
        self._state.bg_path = st.bg_path
        self._state.base_stars = st.base_stars
        self._state.mod_stars = st.mod_stars
        # don't clobber override
        self._chips.update_live_mods(st.live_mods)

        self._hero.set_track(artist=self._state.artist,
                              title=self._state.title,
                              difficulty=self._state.difficulty)
        self._hero.set_stars(base=self._state.base_stars,
                              mod=self._state.mod_stars)
        self._hero.set_background(self._state.bg_path)
        self._recalc()

    # ---- recalc -------------------------------------------------------
    def _on_slider(self, acc: float) -> None:
        self._state.slider_acc = acc
        self._recalc()

    def _recalc(self) -> None:
        rd = compute_render(self._state)
        if rd is not None:
            self._stats.set_stats(ar=rd.ar, od=rd.od, cs=rd.cs, hp=rd.hp,
                                    bpm=int(rd.bpm))
            self._pp.set_pp(rd.pp, rd.accuracy)
            # mod-bumped stars come from RenderData
            self._hero.set_stars(base=self._state.base_stars, mod=rd.stars)
        self._refresh_live_row()
        self._hero.set_pinned(self._state.is_overriding())

    def _refresh_live_row(self) -> None:
        label = self._state.live_row_label()
        if not self._show_live_row_enabled or label is None or self._state.live_play is None:
            self._live.set_content(label=None, pp=0, acc=0, combo=0, misses=0)
            return
        pp = compute_live_pp(self._state)
        lp = self._state.live_play
        self._live.set_content(label=label, pp=pp, acc=lp.accuracy,
                                combo=lp.combo, misses=lp.misses)

    # ---- window behaviour --------------------------------------------
    def _on_drag(self, dx: int, dy: int) -> None:
        self.move(self.pos() + QPoint(dx, dy))

    def _show_settings_menu(self) -> None:
        menu = QMenu(self)

        on_top = QAction("Always on top", menu, checkable=True)
        on_top.setChecked(bool(self.windowFlags() & Qt.WindowStaysOnTopHint))
        on_top.toggled.connect(self._set_always_on_top)
        menu.addAction(on_top)

        show_live = QAction("Show live row", menu, checkable=True)
        show_live.setChecked(self._show_live_row_enabled)
        show_live.toggled.connect(self._set_show_live_row)
        menu.addAction(show_live)

        menu.addSeparator()

        acc_menu = menu.addMenu("Acc range")
        group = QActionGroup(acc_menu); group.setExclusive(True)
        for label, lo, hi in (("90 – 100%", 90.0, 100.0),
                               ("95 – 100%", 95.0, 100.0),
                               ("0 – 100%",  0.0, 100.0)):
            a = QAction(label, acc_menu, checkable=True)
            a.setChecked(self._acc_range == (lo, hi))
            a.triggered.connect(lambda _checked=False, lo=lo, hi=hi: self._set_acc_range(lo, hi))
            group.addAction(a); acc_menu.addAction(a)

        menu.addSeparator()
        reset = QAction("Reset position", menu)
        reset.triggered.connect(lambda: self.move(100, 100))
        menu.addAction(reset)

        # Show menu at the ⋮ button position
        btn = self._hero._pin_btn
        menu.exec(btn.mapToGlobal(btn.rect().bottomRight()))

    def _set_always_on_top(self, on: bool) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.show()  # re-applying flags hides the window on X11

    def _set_show_live_row(self, on: bool) -> None:
        self._show_live_row_enabled = on
        self._refresh_live_row()

    def _set_acc_range(self, lo: float, hi: float) -> None:
        self._acc_range = (lo, hi)
        self._slider.set_range(lo, hi)

    def _restore_persisted(self) -> None:
        d = _load_persisted()
        if "x" in d and "y" in d:
            self.move(int(d["x"]), int(d["y"]))
        if "always_on_top" in d:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(d["always_on_top"]))
        if "show_live_row" in d:
            self._show_live_row_enabled = bool(d["show_live_row"])
        if "acc_range" in d and isinstance(d["acc_range"], list) and len(d["acc_range"]) == 2:
            lo, hi = float(d["acc_range"][0]), float(d["acc_range"][1])
            self._acc_range = (lo, hi)
            self._slider.set_range(lo, hi)

    def closeEvent(self, ev) -> None:
        d = _load_persisted()
        d.update({
            "x": self.x(), "y": self.y(),
            "always_on_top": bool(self.windowFlags() & Qt.WindowStaysOnTopHint),
            "show_live_row": self._show_live_row_enabled,
            "acc_range": [self._acc_range[0], self._acc_range[1]],
        })
        _save_persisted(d)
        try:
            self._poller.stop()
            self._poller.wait(2000)
        except Exception:
            pass
        super().closeEvent(ev)
