# RedPP

EZPP-style osu!(lazer) pp calculator. Two surfaces:

- **CLI** (`redpp.py`) — one-shot, REPL, and tosu-watch modes
- **Desktop app** (`redpp_app/`) — frameless always-on-top panel, mod overrides, live in-play pp

## Download (prebuilt binaries)

Grab the latest release from the [Releases page](https://github.com/R3dWolfie/RedPP/releases):

- **Linux:** `RedPP-x86_64.AppImage` (recommended) or the raw `redpp-linux-x86_64` binary
- **Windows:** `RedPP-windows-x86_64.exe`

No install needed — make executable and run.

## Install (from source)

```bash
python -m venv .venv && source .venv/bin/activate
pip install rosu-pp-py
chmod +x redpp.py
```

To also run the desktop app:
```bash
pip install PySide6
python -m redpp_app
```

## Usage

**One-shot:**
```bash
./redpp.py path/to/map.osu "HDHR 94.30% 8x50 42x100 700x300"
./redpp.py path/to/map.osu "HDHR"           # → 95/97/99/100% preset row
```

**Interactive REPL:**
```bash
./redpp.py path/to/map.osu                  # type score strings, ↑/↓ for history
./redpp.py                                  # uses current tosu map
```

**Watch (auto-poll tosu):**
```bash
./redpp.py -w
./redpp.py -w --mods HDHR --acc 95,98,100
```

Auto-fetch features (omitting `<map>`, watch mode) require [tosu](https://github.com/tosuapp/tosu) running on `http://127.0.0.1:24050`.

## Score grammar

Order-independent. Whatever's missing gets defaulted.

| Token       | Example          | Meaning                              |
|-------------|------------------|--------------------------------------|
| mods        | `HDHR`, `HD HR`  | concat 2-letter acronyms             |
| accuracy    | `94.30%`         |                                      |
| hits        | `8x50`, `3xMiss` | counts per judgement                 |
| combo       | `x1234`, `1234x` | (when not followed by 50/100/300/M)  |
| diff        | `ar9.5 od8 cs4`  | base values, mods apply on top       |
| rate        | `1.5x`           | custom clock rate (overrides DT/HT)  |
| flags       | `stable`, `lazer`| score system (default lazer)         |

## Flags

`--mods`, `--acc`, `--host`, `--port`, `--json`, `--verbose`, `--quiet`, `-w`.

## Desktop app

Compact 280×420 always-on-top panel. Hero strip with the current map's
blurred background, 4 mod chips (HD/HR/DT/FL — clickable to override
osu!'s reported mods for what-if calculations), AR/OD/CS/HP/BPM line
(mod-adjusted), big pp number with cyan S-rank badge, accuracy slider
(default 90–100%), and an in-play row that surfaces real-time pp during
play / spectate / replay. ⋮ menu controls always-on-top, live-row
visibility, accuracy range, and reset position. State persists to
`~/.config/redpp/state.json` (Linux/macOS) or `%APPDATA%\redpp\state.json`
(Windows).

Both surfaces require [tosu](https://github.com/tosuapp/tosu) running on
`127.0.0.1:24050` for live-map auto-detection.

## License

MIT — see [LICENSE](LICENSE). Bundled third-party components (rosu-pp-py,
PySide6, PyInstaller) retain their own licenses, listed in
[NOTICE.md](NOTICE.md).
