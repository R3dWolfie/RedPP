import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QSignalSpy

from redpp_app.state import AppState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_chips_reflect_initial_live_mods(qapp):
    from redpp_app.widgets.mod_chips_row import ModChipsRow, CHIP_ORDER
    state = AppState(live_mods="HDHR")
    row = ModChipsRow(state)
    actives = {c.acronym: c.active for c in row.chips()}
    # 8 chips total across 2 rows; only the live ones light up.
    assert set(actives.keys()) == set(CHIP_ORDER)
    assert actives["HD"] is True and actives["HR"] is True
    assert all(actives[m] is False for m in ("DT", "FL", "EZ", "HT", "NC", "BL"))


def test_chip_layout_has_two_rows(qapp):
    from redpp_app.widgets.mod_chips_row import ModChipsRow, CHIP_ROWS
    assert len(CHIP_ROWS) == 2
    assert all(len(r) == 4 for r in CHIP_ROWS)
    assert "EZ" in CHIP_ROWS[1] and "HT" in CHIP_ROWS[1]
    state = AppState()
    row = ModChipsRow(state)
    # 8 chips total
    assert len(row.chips()) == 8


def test_clicking_chip_enters_override_and_changes_active(qapp):
    from redpp_app.widgets.mod_chips_row import ModChipsRow
    state = AppState(live_mods="HD")
    row = ModChipsRow(state)
    # Click DT
    [c for c in row.chips() if c.acronym == "DT"][0].click()
    assert state.is_overriding()
    assert "DT" in state.effective_mods()
    assert "HD" in state.effective_mods()


def test_revert_returns_to_live(qapp):
    from redpp_app.widgets.mod_chips_row import ModChipsRow
    state = AppState(live_mods="HD")
    row = ModChipsRow(state)
    [c for c in row.chips() if c.acronym == "FL"][0].click()
    assert state.is_overriding()
    row.revert_override()
    assert not state.is_overriding()
    actives = {c.acronym: c.active for c in row.chips()}
    assert actives["HD"] is True and actives["FL"] is False


def test_state_changed_signal_fires_on_chip_click(qapp):
    from redpp_app.widgets.mod_chips_row import ModChipsRow
    state = AppState(live_mods="")
    row = ModChipsRow(state)
    spy = QSignalSpy(row.state_changed)
    [c for c in row.chips() if c.acronym == "HD"][0].click()
    assert spy.count() == 1
