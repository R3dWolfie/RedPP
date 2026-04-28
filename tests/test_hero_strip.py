import pytest
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_hero_strip_basic_text(qapp):
    from redpp_app.widgets.hero_strip import HeroStrip
    h = HeroStrip()
    h.set_track(artist="Treyarch Sound", title="115", difficulty="Extra")
    assert "Treyarch Sound" in h._artist_label.text()
    assert "115" in h._title_label.text()
    assert "Extra" in h._diff_label.text()


def test_hero_strip_stars_label(qapp):
    from redpp_app.widgets.hero_strip import HeroStrip
    h = HeroStrip()
    h.set_stars(base=5.0, mod=8.29)
    assert "8.29" in h._stars_label.text()
    assert not h._chevron.isHidden()


def test_hero_strip_no_chevron_when_unmodded(qapp):
    from redpp_app.widgets.hero_strip import HeroStrip
    h = HeroStrip()
    h.set_stars(base=5.0, mod=5.0)
    assert h._chevron.isHidden()


def test_hero_strip_close_button_emits_close(qapp):
    from redpp_app.widgets.hero_strip import HeroStrip
    h = HeroStrip()
    spy = QSignalSpy(h.close_clicked)
    h._close_btn.click()
    assert spy.count() == 1


def test_hero_strip_pin_button_emits_pin_toggle(qapp):
    from redpp_app.widgets.hero_strip import HeroStrip
    h = HeroStrip()
    spy = QSignalSpy(h.pin_toggled)
    h._pin_btn.click()
    assert spy.count() == 1


def test_hero_strip_drag_emits_signal(qapp):
    from redpp_app.widgets.hero_strip import HeroStrip
    h = HeroStrip()
    h.resize(280, 140)
    spy = QSignalSpy(h.drag_delta)
    press = QMouseEvent(QMouseEvent.MouseButtonPress, QPointF(100, 60),
                         Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    h.mousePressEvent(press)
    move = QMouseEvent(QMouseEvent.MouseMove, QPointF(115, 75),
                        Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
    h.mouseMoveEvent(move)
    assert spy.count() == 1
    dx, dy = spy.at(0)
    assert dx == 15 and dy == 15
