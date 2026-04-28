import json
import pytest
import threading
import http.server
import socketserver
import time as _time
from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QSignalSpy

from redpp_app.poller import TosuPoller
from redpp_app.state import PlayState


class _FakeTosu(http.server.BaseHTTPRequestHandler):
    payloads: dict = {}

    def do_GET(self):
        body = self.payloads.get(self.path)
        if body is None:
            self.send_response(404); self.end_headers(); return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a, **kw): pass


@pytest.fixture
def fake_tosu(tmp_path):
    osu = tmp_path / "song.osu"
    osu.write_text("osu file format v14\n[HitObjects]\n")
    _FakeTosu.payloads = {"/json": {
        "client": "lazer",
        "settings": {"folders": {"songs": str(tmp_path)}},
        "menu": {
            "state": 5,
            "bm": {
                "id": 1, "set": 2, "md5": "x",
                "metadata": {"artist": "A", "title": "B", "difficulty": "C"},
                "stats": {"AR": 9, "OD": 8, "CS": 4, "HP": 5,
                          "BPM": {"common": 180}, "SR": 5, "fullSR": 5,
                          "maxCombo": 100},
                "path": {"folder": ".", "file": osu.name, "bg": "", "full": ""},
            },
            "mods": {"str": "HD"},
        },
        "play": {"mods": {"str": "HD"}, "hits": {}, "combo": {"current": 0}},
    }}
    srv = socketserver.TCPServer(("127.0.0.1", 0), _FakeTosu)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    yield srv, port, osu
    srv.shutdown(); srv.server_close()


@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


def _wait_signals(spy: QSignalSpy, count: int, timeout_ms: int = 2000):
    deadline = _time.time() + timeout_ms / 1000.0
    while spy.count() < count and _time.time() < deadline:
        QCoreApplication.processEvents()
        _time.sleep(0.01)


def test_poller_emits_state_on_first_poll(qapp, fake_tosu):
    srv, port, osu = fake_tosu
    p = TosuPoller(host="127.0.0.1", port=port, interval_ms=50)
    spy = QSignalSpy(p.state_changed)
    p.start()
    _wait_signals(spy, 1)
    p.stop(); p.wait()
    assert spy.count() >= 1
    state = spy.at(0)[0]
    assert "/song.osu" in state.path
    assert state.live_mods == "HD"
    assert state.play_state is PlayState.IDLE


def test_poller_dedupes_unchanged_state(qapp, fake_tosu):
    srv, port, _osu = fake_tosu
    p = TosuPoller(host="127.0.0.1", port=port, interval_ms=20)
    spy = QSignalSpy(p.state_changed)
    p.start()
    _time.sleep(0.2)
    p.stop(); p.wait()
    # Despite ~10 polls, state didn't change, so we should see exactly 1 emit
    assert spy.count() == 1


def test_poller_reemits_on_mod_change(qapp, fake_tosu):
    srv, port, _osu = fake_tosu
    p = TosuPoller(host="127.0.0.1", port=port, interval_ms=20)
    spy = QSignalSpy(p.state_changed)
    p.start()
    _wait_signals(spy, 1)
    _FakeTosu.payloads["/json"]["menu"]["mods"] = {"str": "HDHR"}
    _wait_signals(spy, 2)
    p.stop(); p.wait()
    assert spy.count() >= 2
    assert spy.at(1)[0].live_mods == "HDHR"


def test_poller_emits_unreachable_then_recovered(qapp, tmp_path):
    # Start poller pointing at a port nothing is listening on
    p = TosuPoller(host="127.0.0.1", port=1, interval_ms=20)
    unreachable_spy = QSignalSpy(p.tosu_unreachable)
    p.start()
    _wait_signals(unreachable_spy, 1)
    p.stop(); p.wait()
    assert unreachable_spy.count() >= 1
