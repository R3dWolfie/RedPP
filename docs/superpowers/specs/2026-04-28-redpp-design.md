# RedPP — design

Single-file CLI (`redpp.py`) for osu!(lazer) pp calculation. Three modes:
one-shot, interactive REPL, and watch (auto-poll tosu).

## Scope (frozen)

User's prompt-spec is the source of truth for grammar, output format, and
tosu integration paths. This document captures only:

1. Module layout for the single file.
2. The 9 UX improvements approved (option A in brainstorm).
3. API ground truth verified against rosu-pp-py 4.0.2 / Python 3.14.

## API ground truth (rosu-pp-py 4.0.2, verified)

- `Performance(**kwargs)` constructor accepts `accuracy, mods, n300, n100,
  n50, misses, combo, lazer, clock_rate, ar, cs, od, hp, fixed_ar,
  fixed_cs, fixed_od, fixed_hp`. Setter equivalents (`set_accuracy`,
  `set_mods`, …) also exist; kwargs path is preferred for clarity.
- `mods=` accepts `"HDHR"`, `["HD","HR"]`, int bitflag, or `[]`. We pass
  the canonical concatenated string (e.g. `"HDHR"`) or omit on no-mods.
- `BeatmapAttributesBuilder(map=bmap, mods=...).build()` returns object
  with `.ar .od .cs .hp .clock_rate`. Use this for the header line — it
  applies mod scaling, including the DT/HT/clock-rate ramp on AR/OD.
- `bmap.bpm` is the base BPM; multiply by `clock_rate` for displayed BPM.
- `bmap.is_suspicious()` — gate every calculation.
- `PerformanceAttributes`: `.pp .pp_aim .pp_speed .pp_accuracy
  .pp_difficulty .pp_flashlight .difficulty`.
- `DifficultyAttributes.stars` and `.max_combo` for header / combo line.

Note: the JS-binding-only `ar_with_mods` flag does NOT exist in Python.
Use `fixed_ar=False` (the default) when AR/OD/CS/HP overrides are BASE
values.

## File layout (single file, ~500-600 lines)

```
redpp.py
├── shebang + imports
├── constants
│   ├── KNOWN_MODS = {"EZ","NF","HT","DC","HR","SD","PF","DT","NC","HD",
│   │                  "FL","RX","AP","SO","TD","CL","BL","TC"}
│   ├── DEFAULT_ACC_PRESETS = (95.0, 97.0, 99.0, 100.0)
│   └── ANSI color constants (gated by IS_TTY)
├── score-string parser  (parse_score_string)
├── tosu client          (TosuClient: fetch_state, _resolve_path, _extract_mods)
├── beatmap cache        (load_bmap with (path, mtime) memoization)
├── calculation core     (calc_one, calc_presets — both return tuples for rendering)
├── renderers            (render_header, render_score_line, render_preset_row,
│                        render_verbose_breakdown)
├── modes                (run_oneshot, run_repl, run_watch)
└── main(argv)           (argparse, dispatch)
```

## The 9 approved UX improvements

### Free wins (no flag, always on)

1. **`import readline` in REPL** — instantly enables ↑/↓ history, line
   editing, ctrl-A/E. Single import. `readline.set_history_length(500)`.
2. **ANSI color when stdout is a TTY** — auto-disabled if `not
   sys.stdout.isatty()` or `NO_COLOR` env set. Stars cyan, pp green-bold,
   mods yellow, dim grey for footer/heartbeat. Plain text output is
   byte-identical to the spec's example when piped.
3. **Beatmap cache `(path, mtime) → Beatmap`** — module-level dict.
   REPL/watch re-renders are instant when map hasn't changed on disk.
4. **Unknown mod → `difflib.get_close_matches`** suggestion. `"ZZ" → did
   you mean DT?` (or just `unknown mod 'ZZ'` if no close match).
5. **No-acc-no-hits → preset row** — if score-string parses to no
   accuracy AND no hit counts AND no combo, render the same multi-acc row
   as watch mode rather than calculating "100% FC". So `redpp.py map.osu
   "HDHR"` shows 95/97/99/100% for HDHR.

### Flagged (off by default unless noted)

6. **`--json`** — emits one JSON object per render to stdout instead of
   the human format. Stable schema: `{filename, stars, ar, od, cs, hp,
   bpm, clock_rate, mods, combo, max_combo, hits:{n300,n100,n50,miss},
   acc, pp}` for one-shot; `{...header..., presets:[{acc, pp}, ...]}` for
   watch / no-acc shortcut.
7. **`--verbose`** — adds a second line breaking out
   `aim X.X | speed X.X | acc X.X | diff X.X | fl X.X` from
   PerformanceAttributes.
8. **Watch mode footer** — dim line: `(polling 24050 · 14:02:11)`.
   Updated on every poll, not just on state-change. ANSI-cleared/redrawn
   so it doesn't accumulate. Hidden if `--quiet`.
9. **Watch mode graceful tosu-down** — connection failures surface as one
   dim `(tosu unreachable, retrying…)` line. Exponential backoff capped
   at 5s. When connection recovers, line clears and normal output
   resumes. No tracebacks.

## Score-string parser order

Locked from spec, repeated here for clarity. Each step strips its tokens
from the working string before the next step runs:

1. `stable` / `lazer` keywords → `lazer: bool`
2. `ar9.5` / `od8` / `cs4` / `hp5` (case-insensitive) → diff overrides,
   `fixed_*=False`
3. `1.5x` clock rate — regex must NOT match if followed by
   `50|100|300|m|miss` (case-insensitive). Example unwanted match: `8x50`.
   Implementation: `(?<![0-9])(\d+(?:\.\d+)?)x(?![0-9]*(?:50|100|300|m))`
   plus a value-range sanity check (0.5–3.0).
4. Hit counts: `\d+x(50|100|300|miss|m)` (case-insensitive). Strip.
5. Combo: `\d+x` or `x\d+` AFTER hits stripped. Strip.
6. Accuracy: `\d+(\.\d+)?%`.
7. Remaining 2-letter caps: validate against KNOWN_MODS, error with
   suggestion on unknown.

## Watch loop

```
while True:
    try:
        state = tosu.fetch_state()
    except ConnectionError:
        show_unreachable(); backoff(); continue
    clear_unreachable()
    if state is None:
        show_no_map_once()
        sleep(0.5); continue
    key = (state.path, state.mods_str)
    if key != last_key:
        render(state)
        last_key = key
    update_footer()  # (9) — every tick, not just on change
    sleep(0.5)
```

`mods_override` (from `--mods`) replaces `state.mods_str` in the dedupe
key so pinning still re-renders on map change.

KeyboardInterrupt → clean exit, leave terminal cursor visible.

## Testing strategy

Per the spec's "build incrementally and TEST as you go":

1. **Parser** — table-driven test cases inline in `if __name__ ...
   tests`, runnable via `python redpp.py --self-test` (hidden flag).
   Cases include the 6 from the spec plus a few edge cases (`8x50` not
   eaten by clock-rate; `x650 5xMiss` order-independence; case
   insensitivity on mods).
2. **Calculation** — synthetic .osu file with proper `[TimingPoints]`
   (the probe earlier had `bpm=inf` due to missing timing — must include
   a real timing point). Verify pp is positive and changes monotonically
   with acc.
3. **Watch** — fake tosu with `http.server.BaseHTTPRequestHandler` on a
   throwaway port, threading.Thread. Mutate canned JSON between sleeps,
   assert dedupe key changes trigger re-render exactly once.

Tests live in a separate `test_redpp.py` adjacent to redpp.py; not in
the deliverable but kept in the repo for sanity.

## Deliverables

1. `/var/home/red/PycharmProjects/RedPP/redpp.py` — executable, hashbang.
2. `/var/home/red/PycharmProjects/RedPP/README.md` — install + 3 modes +
   tosu note. Short.
3. `/var/home/red/PycharmProjects/RedPP/test_redpp.py` — parser +
   fake-tosu integration tests. Not required for the user but kept.

## Out of scope (explicitly skipped)

- Aliases file (`@myrun`).
- Tab-completion of mod names in REPL (readline history covers it).
- ASCII bar charts in watch mode.
- Multi-mode support (only osu!std — taiko/catch/mania left for later).
- Score submission, replay parsing, anything network-write.
