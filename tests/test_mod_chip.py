import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_mod_chip_default_inactive(qapp):
    from redpp_app.widgets.mod_chip import ModChip
    c = ModChip("HD")
    assert c.acronym == "HD"
    assert c.active is False


def test_mod_chip_set_active(qapp):
    from redpp_app.widgets.mod_chip import ModChip
    c = ModChip("HR")
    c.set_active(True)
    assert c.active is True


def test_mod_chip_emits_toggle_on_click(qapp):
    from redpp_app.widgets.mod_chip import ModChip
    c = ModChip("DT")
    spy = QSignalSpy(c.toggled_chip)
    c.click()
    assert spy.count() == 1
    assert spy.at(0)[0] == "DT"


def test_mod_chip_acronym_uppercased(qapp):
    from redpp_app.widgets.mod_chip import ModChip
    c = ModChip("hd")
    assert c.acronym == "HD"
