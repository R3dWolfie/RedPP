# RedPP App — design

Compact always-on-top desktop panel that mirrors the osu!Glean popup style
(see reference screenshot). Recreates the same visual language as a real
cross-platform application driven by tosu data, with a what-if accuracy
slider and clickable mod overrides.

## Scope (frozen)

- **Form**: PySide6 desktop app **+** a minimal browser extension.
- **Backend (app)**: reuses `redpp.py` (`parse_score_string`,
  `TosuClient`, `load_bmap`, `calc_one`, `calc_presets`, `RenderData`)
  verbatim.
- **OS support**: Linux + Windows for the app. macOS likely works but
  isn't tested. Extension is browser-only (Chrome + Firefox).
- **Distribution**: per-OS PyInstaller bundle (`redpp-app`); WebExtension
  zip uploaded to Chrome Web Store / Firefox AMO.
- **Build order**: app first (full feature set), extension second.
- **Parked for later**: full-dashboard window (the original "B" option).

## Window

- **Chrome**: frameless, rounded corners (8px), drop-shadow.
- **Size**: 280 × 420 px fixed (no resize).
- **Drag-to-move**: any pointer-down on the hero strip moves the window
  *except* on the × and ⋮ buttons (buttons consume the event first).
- **Always-on-top**: enabled by default, toggleable via a small ⋮ menu
  button in the top-right of the hero strip.
- **Close**: small × button, also in the top-right of the hero strip.
- **Position memory**: saved to `~/.config/redpp/state.json`
  (Linux/macOS) or `%APPDATA%\redpp\state.json` (Windows). Reused on next
  launch.

## Layout (top to bottom)

### 1. Hero strip — height 140 px

Background:
- Blurred beatmap image. Source priority:
  1. tosu's `menu.bm.path.bg` resolved against `settings.folders.songs`
     (the lazer SHA256 file). Read into a QPixmap, Gaussian-blurred
     server-side at load time, cached by hash.
  2. Fallback: `https://assets.ppy.sh/beatmaps/<setid>/covers/cover.jpg`.
  3. Final fallback: solid dark gradient.
- Dim overlay (rgba 0,0,0,0.45) for text contrast.

Top-right corner:
- Stars rating, large bold (e.g. `8.29`).
- Gold up-chevron icon `⏶⏶` when mod-adjusted SR > base SR.
- Right of those: ⋮ pin/unpin button, then × close. Both 18×18 px.

Bottom-left:
- Artist (small, 11pt, dim) — e.g. `[Crystallized Heartache]`.
- Title (bold, 18pt) — e.g. `The Frozen Land`.
- Difficulty (medium, 12pt, off-white) — e.g. `Fellowship`.

### 2. Mod chips row — height 60 px

- Four hexagonal chips, evenly spaced: **HD · HR · DT · FL**.
- Active state: gold fill, white text.
- Inactive state: dim gold outline only.
- Hover state: subtle highlight.
- Clickable to override (see "State machine" below).
- 2-letter mod abbreviation rendered inside each hex.

### 3. Stats line — height 24 px

Single line, 11pt, gray:
`AR: x.xx  OD: x.xx  CS: x.xx  HP: x.xx  BPM: nnn`

Values are mod-adjusted (from `BeatmapAttributesBuilder`).

### 4. PP result row — height 56 px

- Left: 32×32 px cyan rounded-square `S` rank badge.
- Right: bold 22pt `<NN>pp for <NN.N>%`.
- pp updates as the slider drags (no debounce — direct calc).

### 5. Accuracy slider — height 48 px

- Label `Accuracy: <NN.N>%` above (11pt, gray).
- Yellow track, white knob.
- Range: 90.0 – 100.0%, step 0.1% (default). Settings → Acc range can
  widen to 95–100 or 0–100; the chosen range remaps the slider but the
  pp number always treats the slider value as the literal accuracy.
- Default value: 100.0%.
- The slider is the **primary interaction** in every state.

### 6. Live in-play row (additive, not replacement) — height 24 px

Visible only when osu! state is `playing` / `spectating` / `replay`:

| osu! state          | Label         |
|---------------------|---------------|
| playing (self)      | `Now:`        |
| spectating          | `Spectating:` |
| watching replay     | `Replay:`     |

Format: `<Label> <pp>pp · <acc>% · <combo>x · <misses>m`. Updates every
500 ms while the play is active. The slider remains primary; this row is
informational. A Settings toggle disables it entirely.

### 7. Footer — height 20 px

`RedPP v0.x.x` (left-aligned, 9pt, dim).

## State machine

Two orthogonal axes:

**Mod axis: live-mods vs override-mods.**
- *Live* (default): chips and pp reflect tosu's current mods.
- *Override*: triggered the moment any chip is clicked. Title gains a
  small `[pinned]` chip; a `↺` revert button appears next to it. Click
  revert → back to live. Switching maps does NOT clear override (intentional).

**Display axis: idle vs in-play.**
- *Idle*: state ∈ {menu, song-select, results, ...}. Live-pp row hidden.
- *In-play*: state ∈ {playing, spectating, replay}. Live-pp row visible
  with the appropriate label.

The two axes are independent — overriding mods while spectating keeps
the spectator's live row showing the host's actual pp (with the host's
actual mods, not the override).

## Backend integration

- Polling thread: pulls `TosuClient.fetch_state()` every 500 ms. Same
  client class as the CLI watch mode.
- Dedupe key per render: `(path, effective_mods, slider_acc,
  in_play_pp_signature)`. The first three trigger a full preset
  recompute; the last only redraws the live row.
- Calculation paths:
  - **Slider drag**: `calc_one(path, ParsedScore(mods=effective_mods,
    accuracy=slider_acc, lazer=True))` → `RenderData.pp` for the big
    number, `.ar/.od/.cs/.hp/.bpm` for the stats line.
  - **Live in-play**: `calc_one(path, ParsedScore(mods=tosu_mods,
    n300=tosu.hits.300, n100=..., n50=..., misses=...,
    combo=tosu.combo.current, lazer=True))` for the actual current pp.
- Beatmap cache (`_BMAP_CACHE`) shared with the CLI — already mtime-keyed.

## Threading model

- Qt main thread owns all widgets.
- One `QThread` runs the tosu poller. Emits a `state_changed` signal
  with a small `AppState` dataclass.
- Slider changes are handled on the main thread (calc takes <5 ms, no
  threading needed).
- Hero image loading runs on a `QThreadPool` worker so blur doesn't
  stutter the UI.

## Settings

Small ⋮ menu (top-right of hero) opens a popover:
- ✓ Always on top
- ✓ Show live in-play row
- — Acc range (90–100% / 95–100% / 0–100%)
- — Reset window position

Persisted to `state.json`.

## File layout

```
RedPP/
├── redpp.py                  # existing CLI, untouched
├── redpp_app/
│   ├── __init__.py
│   ├── __main__.py           # entry point: `python -m redpp_app`
│   ├── main_window.py        # the panel, layout, drag, settings menu
│   ├── poller.py             # QThread wrapping TosuClient
│   ├── widgets/
│   │   ├── hero_strip.py     # bg image + title + close/pin
│   │   ├── mod_chip.py       # hexagonal toggle button
│   │   ├── pp_result.py      # S badge + big number
│   │   ├── acc_slider.py     # styled QSlider
│   │   └── live_row.py       # in-play info line
│   ├── theme.qss             # QSS stylesheet for dark + colors
│   └── assets/
│       ├── s_rank.png        # 64×64 cyan S badge
│       └── chevron_up.png    # gold mod-bump indicator
├── pyproject.toml            # adds pyside6, pyinstaller as deps
├── build_app.sh / build_app.ps1   # PyInstaller wrappers
└── tests/
    ├── test_app_state.py     # state-machine transitions, mod override
    └── test_poller.py        # poller emits expected signals
```

## Distribution

PyInstaller one-file mode per OS:
```bash
.venv/bin/pyinstaller --onefile --windowed --name redpp \
  --add-data "redpp_app/theme.qss:redpp_app" \
  --add-data "redpp_app/assets:redpp_app/assets" \
  redpp_app/__main__.py
```

Result: ~50 MB binary on Linux, ~60 MB on Windows. Single file, no
runtime install needed by end users.

## Browser extension — minimal scope

A second deliverable, built **after** the app ships. Strictly: "what is
this map worth at <acc> with <mods>?" — nothing else. No tosu, no live
pp, no spectate awareness, no settings.

### Surface

- Manifest v3 WebExtension, packaged for both Chrome and Firefox from
  one source tree (Firefox needs `browser_specific_settings` block; the
  rest is identical).
- Activates on osu.ppy.sh and ppy.sh beatmap pages
  (`*://osu.ppy.sh/beatmapsets/*`, `*://osu.ppy.sh/b/*`).
- Toolbar icon → popup. No content script, no in-page injection.

### Visual design

Same panel as the app, minus the live-row, minus the settings menu,
minus the close/pin buttons (popup auto-dismisses on outside click).
Hero strip uses osu's CDN cover (`assets.ppy.sh/beatmaps/<setid>/...`)
since there's no local file. Same mod chips, same stats line, same pp
result, same slider, same `RedPP vX.Y.Z` footer.

### Calculation

`rosu-pp-js` (the official WASM bindings of rosu-pp). Bundled into the
extension (~600 KB). Same algorithm as the app, just running in the
browser. No backend, no API key.

### Beatmap acquisition

- Beatmap ID parsed from the active tab URL.
- `.osu` file fetched from `https://osu.ppy.sh/osu/<id>` (anonymous
  CDN endpoint, no auth, returns the raw file).
- Cached in `chrome.storage.session` (per-tab, evicted on browser
  close).

### File layout

```
RedPP/
└── redpp_ext/
    ├── manifest.json
    ├── popup/
    │   ├── popup.html
    │   ├── popup.css
    │   ├── popup.js              # bootstraps, renders, wires events
    │   ├── calc.js               # thin wrapper over rosu-pp-js
    │   └── beatmap.js            # fetch + cache .osu
    ├── icons/                    # 16/32/48/128 px toolbar icons
    ├── vendor/
    │   └── rosu_pp_js_bg.wasm    # checked in, version-pinned
    └── build_ext.sh              # zips Chrome + Firefox bundles
```

### Out of extension scope (explicit)

- Live tosu integration.
- Override-vs-live mode (everything is "what-if" by definition).
- In-page injection or page-level overlays.
- Score submission, replays, leaderboards.

## Out of scope (whole project, explicit)

- Full dashboard window (option B) — parked.
- Score submission, replay parsing, leaderboards.
- macOS-specific polish (window vibrancy, etc.).
- Multi-mode support (only osu!std — taiko/catch/mania use the CLI for now).
- Auto-update.
