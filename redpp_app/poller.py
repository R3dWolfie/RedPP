"""Background QThread that polls tosu and emits AppState updates.

Reuses the existing redpp.TosuClient for HTTP, then routes the /json
payload through tosu_state.extract_state().
"""
from __future__ import annotations
import time
from PySide6.QtCore import QThread, Signal

import sys
from pathlib import Path
# redpp.py is in the parent of this package — make it importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
import redpp  # noqa: E402  -- side-effect import order

from .state import AppState
from .tosu_state import extract_state


class TosuPoller(QThread):
    """Polls tosu's /json endpoint, emits state_changed when relevant
    fields change. Emits tosu_unreachable on connection failure (once
    per failure burst) and tosu_recovered when it comes back."""

    state_changed = Signal(object)         # AppState
    tosu_unreachable = Signal()
    tosu_recovered = Signal()

    def __init__(self, host: str = "127.0.0.1", port: int = 24050,
                 interval_ms: int = 500) -> None:
        super().__init__()
        self._client = redpp.TosuClient(host=host, port=port, timeout=1.0)
        self._interval_ms = interval_ms
        self._stop = False
        self._last_key: tuple | None = None
        self._unreachable = False
        self._backoff_ms = interval_ms

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        # Use tosu's gosumemory-compatible /json endpoint directly via
        # urllib (TosuClient.fetch_state hides the raw payload, but we
        # need the full thing for our extractor).
        import urllib.request, urllib.error, json as _json
        url = f"{self._client.base}/json"
        while not self._stop:
            try:
                with urllib.request.urlopen(url, timeout=self._client.timeout) as r:
                    if r.status != 200:
                        self._sleep_ms(self._interval_ms); continue
                    payload = _json.loads(r.read().decode("utf-8"))
                if self._unreachable:
                    self._unreachable = False
                    self._backoff_ms = self._interval_ms
                    self.tosu_recovered.emit()
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
                if not self._unreachable:
                    self._unreachable = True
                    self.tosu_unreachable.emit()
                self._sleep_ms(self._backoff_ms)
                self._backoff_ms = min(self._backoff_ms * 2, 5000)
                continue

            state = extract_state(payload)
            if state is not None:
                key = (state.path, state.live_mods, state.play_state,
                       state.live_play and (state.live_play.n300, state.live_play.n100,
                                             state.live_play.n50, state.live_play.misses,
                                             state.live_play.combo))
                if key != self._last_key:
                    self._last_key = key
                    self.state_changed.emit(state)
            self._sleep_ms(self._interval_ms)

    def _sleep_ms(self, ms: int) -> None:
        # Sleep in small chunks so .stop() is responsive.
        deadline = time.monotonic() + ms / 1000.0
        while not self._stop and time.monotonic() < deadline:
            time.sleep(0.02)
