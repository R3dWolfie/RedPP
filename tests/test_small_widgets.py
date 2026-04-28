import pytest
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_stats_line_format(qapp):
    from redpp_app.widgets.stats_line import StatsLine
    s = StatsLine()
    s.set_stats(ar=10.0, od=10.0, cs=5.59, hp=6.30, bpm=200)
    txt = s.text()
    assert "AR: 10.00" in txt and "OD: 10.00" in txt
    assert "CS: 5.59" in txt and "HP: 6.30" in txt
    assert "BPM: 200" in txt


def test_pp_result_format(qapp):
    from redpp_app.widgets.pp_result import PPResult
    p = PPResult()
    p.set_pp(905.4321, 99.5)
    assert "905pp" in p._label.text()
    assert "99.5%" in p._label.text()


def test_acc_slider_emits_value(qapp):
    from redpp_app.widgets.acc_slider import AccSlider
    s = AccSlider()
    spy = QSignalSpy(s.acc_changed)
    s.set_value(99.5)
    assert spy.count() == 1
    assert abs(spy.at(0)[0] - 99.5) < 0.01


def test_acc_slider_range_widening(qapp):
    from redpp_app.widgets.acc_slider import AccSlider
    s = AccSlider()
    s.set_range(0.0, 100.0)
    s.set_value(50.0)
    assert abs(s.value() - 50.0) < 0.01


def test_live_row_hidden_when_no_label(qapp):
    from redpp_app.widgets.live_row import LiveRow
    r = LiveRow()
    r.set_content(label=None, pp=0, acc=0, combo=0, misses=0)
    # Use isHidden() — Qt's isVisible() cascades through parents on
    # widgets that have never been shown, so it would always be False.
    assert r.isHidden() or r._label.text() == ""


def test_live_row_visible_with_label(qapp):
    from redpp_app.widgets.live_row import LiveRow
    r = LiveRow()
    r.set_content(label="Spectating:", pp=247.0, acc=98.3, combo=412, misses=2)
    assert "Spectating:" in r.text()
    assert "247" in r.text()
    assert "98.30" in r.text() or "98.3" in r.text()


def test_footer_shows_version(qapp):
    from redpp_app.widgets.footer import Footer
    f = Footer("0.1.0")
    assert "RedPP" in f.text()
    assert "0.1.0" in f.text()
