# RedPP

EZPP-style osu!(lazer) pp calculator. One file, three modes.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install rosu-pp-py
chmod +x redpp.py
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
