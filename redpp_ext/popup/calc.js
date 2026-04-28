/* Thin wrapper over rosu-pp-js. Initializes the WASM module once,
   exposes compute() returning the data the popup needs. */

import init, * as rosu from "../vendor/rosu_pp_js.js";

let _ready = null;
function ensureReady() {
  if (_ready) return _ready;
  // Resolve the WASM URL relative to the extension root. chrome.runtime
  // works in both Chrome and Firefox; "browser" is a Firefox alias.
  const rt = (typeof chrome !== "undefined" && chrome.runtime)
    ? chrome.runtime
    : (typeof browser !== "undefined" ? browser.runtime : null);
  const wasmUrl = rt ? rt.getURL("vendor/rosu_pp_js_bg.wasm") : "../vendor/rosu_pp_js_bg.wasm";
  _ready = init(wasmUrl);
  return _ready;
}

/** Compute pp + mod-adjusted attributes for a beatmap.
 *
 *  @param {Uint8Array} osuBytes  - raw .osu file bytes
 *  @param {string}     mods      - concatenated 2-letter acronyms ("HDHR")
 *  @param {number}     accuracy  - 0..100
 *  @returns {Promise<{
 *    pp: number, stars: number, baseStars: number,
 *    ar: number, od: number, cs: number, hp: number,
 *    bpm: number, clockRate: number, maxCombo: number
 *  }>}
 */
export async function compute(osuBytes, mods, accuracy) {
  await _step("init", () => ensureReady());
  const bmap = await _step("Beatmap", () => new rosu.Beatmap(osuBytes));
  try {
    if (await _step("isSuspicious", () => bmap.isSuspicious())) {
      throw new Error("(suspicious — refusing to calculate)");
    }
    const bpm    = await _step("bmap.bpm", () => bmap.bpm);
    const attrs  = await _step("attrs.build", () => {
      const a = { map: bmap };
      if (mods) a.mods = mods;
      return new rosu.BeatmapAttributesBuilder(a).build();
    });
    try {
      const ar = attrs.ar, od = attrs.od, cs = attrs.cs, hp = attrs.hp;
      const clockRate = attrs.clockRate;

      const basePerf = await _step("base perf", () =>
        new rosu.Performance({ lazer: true, accuracy: 100 }).calculate(bmap)
      );
      const baseStars = basePerf.difficulty.stars;
      basePerf.free?.();

      const perfArgs = { lazer: true, accuracy };
      if (mods) perfArgs.mods = mods;
      const perf = await _step("perf", () =>
        new rosu.Performance(perfArgs).calculate(bmap)
      );
      const out = {
        pp: perf.pp,
        stars: perf.difficulty.stars,
        baseStars,
        ar, od, cs, hp, clockRate,
        bpm: bpm * clockRate,
        maxCombo: perf.difficulty.maxCombo,
      };
      perf.free?.();
      return out;
    } finally {
      attrs.free?.();
    }
  } finally {
    bmap.free?.();
  }
}

/* Wraps a step so failures surface WHICH step blew up. Async-safe. */
async function _step(name, fn) {
  try {
    return await fn();
  } catch (e) {
    const msg = (e && (e.message || e.toString())) || "(unknown)";
    const err = new Error(`${name}: ${msg}`);
    err.stack = e?.stack;
    throw err;
  }
}

/** Lightweight metadata read straight from the .osu text (no WASM needed).
 *  Returns {artist, title, version, setId} for the hero strip. */
export function readMetadata(osuBytes) {
  const text = new TextDecoder("utf-8").decode(osuBytes.slice(0, 4096));
  const meta = {};
  const map = { Artist: "artist", Title: "title", Version: "version",
                 BeatmapSetID: "setId" };
  for (const [k, prop] of Object.entries(map)) {
    const re = new RegExp(`^${k}\\s*:\\s*(.+)$`, "m");
    const m = text.match(re);
    if (m) meta[prop] = m[1].trim();
  }
  if (meta.setId) meta.setId = parseInt(meta.setId, 10);
  return meta;
}
