#!/var/home/red/PycharmProjects/RedPP/.venv/bin/python3
"""redpp — EZPP-style osu!(lazer) pp calculator (one-shot / REPL / watch)."""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path

import rosu_pp_py as rosu

KNOWN_MODS = {"EZ","NF","HT","DC","HR","SD","PF","DT","NC","HD",
              "FL","RX","AP","SO","TD","CL","BL","TC"}
DEFAULT_ACC_PRESETS = (95.0, 97.0, 99.0, 100.0)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 24050
POLL_INTERVAL = 0.5

IS_TTY = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
def _c(code: str, s: str) -> str:
    return f"\x1b[{code}m{s}\x1b[0m" if IS_TTY else s
CYAN  = lambda s: _c("36", s)
GREEN = lambda s: _c("1;32", s)
YELL  = lambda s: _c("33", s)
DIM   = lambda s: _c("2", s)
BOLD  = lambda s: _c("1", s)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="redpp", description="EZPP-style osu!(lazer) pp calculator")
    ap.add_argument("map", nargs="?", help=".osu file path (omit to fetch from tosu)")
    ap.add_argument("score", nargs="?", help='score string e.g. "HDHR 94.30%% 8x50 42x100 700x300"')
    ap.add_argument("-w", "--watch", action="store_true", help="auto-poll tosu, re-render on change")
    ap.add_argument("--mods", help="pin mods in watch mode (e.g. HDHR)")
    ap.add_argument("--acc", help="comma-separated acc presets (default 95,97,99,100)")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--json", dest="as_json", action="store_true", help="machine-readable output")
    ap.add_argument("--verbose", action="store_true", help="show pp_aim/speed/acc breakdown")
    ap.add_argument("--quiet", action="store_true", help="hide watch-mode footer")
    ap.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    print("redpp skeleton — args:", args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
