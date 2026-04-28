"""Main panel — composes all widgets and wires signals."""
from __future__ import annotations
import json
import os
from pathlib import Path
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                  QPushButton)

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
        self._hero.pin_toggled.connect(self._toggle_always_on_top)
        outer.addWidget(self._hero)

        self._chips = ModChipsRow(self._state, self)
        self._chips.state_changed.connect(self._recalc)
        outer.addWidget(self._chips)

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

    def _refresh_live_row(self) -> None:
        label = self._state.live_row_label()
        if label is None or self._state.live_play is None:
            self._live.set_content(label=None, pp=0, acc=0, combo=0, misses=0)
            return
        pp = compute_live_pp(self._state)
        lp = self._state.live_play
        self._live.set_content(label=label, pp=pp, acc=lp.accuracy,
                                combo=lp.combo, misses=lp.misses)

    # ---- window behaviour --------------------------------------------
    def _on_drag(self, dx: int, dy: int) -> None:
        self.move(self.pos() + QPoint(dx, dy))

    def _toggle_always_on_top(self) -> None:
        flags = self.windowFlags()
        on_top = bool(flags & Qt.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, not on_top)
        self.show()  # re-applying flags hides the window on X11

    def _restore_persisted(self) -> None:
        d = _load_persisted()
        if "x" in d and "y" in d:
            self.move(int(d["x"]), int(d["y"]))

    def closeEvent(self, ev) -> None:
        d = _load_persisted()
        d.update({"x": self.x(), "y": self.y()})
        _save_persisted(d)
        try:
            self._poller.stop()
            self._poller.wait(2000)
        except Exception:
            pass
        super().closeEvent(ev)
