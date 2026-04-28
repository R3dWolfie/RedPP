/* Thin wrapper over rosu-pp-js. Initializes the WASM module once,
   exposes computeFromBytes() returning the data the popup needs. */

import init, * as rosu from "../vendor/rosu_pp_js.js";

let _ready = null;
function ensureReady() {
  if (_ready) return _ready;
  // Resolve the WASM URL relative to the extension root.
  const wasmUrl = chrome.runtime.getURL("vendor/rosu_pp_js_bg.wasm");
  _ready = init({ module_or_path: wasmUrl });
  return _ready;
}

/** Compute pp + mod-adjusted attributes for a beatmap.
 *
 *  @param {Uint8Array} osuBytes - raw .osu file bytes
 *  @param {string}     mods     - concatenated 2-letter acronyms ("HDHR")
 *  @param {number}     accuracy - 0-100
 *  @returns {Promise<{pp:number, stars:number, baseStars:number,
 *                     ar:number, od:number, cs:number, hp:number,
 *                     bpm:number, clockRate:number, maxCombo:number}>}
 */
export async function compute(osuBytes, mods, accuracy) {
  await ensureReady();

  const bmap = new rosu.Beatmap(osuBytes);
  if (bmap.suspicious) {
    bmap.free();
    throw new Error("(suspicious — refusing to calculate)");
  }

  // Mod-adjusted attributes for the header.
  const attrsBuilder = new rosu.BeatmapAttributesBuilder({ map: bmap });
  if (mods) attrsBuilder.mods = mods;
  const attrs = attrsBuilder.build();

  // Base difficulty (no mods) — used for the chevron decision.
  const baseDiff = new rosu.Difficulty({}).calculate(bmap);

  // Performance with current mods + accuracy.
  const perfArgs = { accuracy, lazer: true };
  if (mods) perfArgs.mods = mods;
  const perf = new rosu.Performance(perfArgs).calculate(bmap);
  const stars = perf.difficulty.stars;
  const maxCombo = perf.difficulty.maxCombo;
  const pp = perf.pp;

  const result = {
    pp,
    stars,
    baseStars: baseDiff.stars,
    ar: attrs.ar,
    od: attrs.od,
    cs: attrs.cs,
    hp: attrs.hp,
    bpm: bmap.bpm * attrs.clockRate,
    clockRate: attrs.clockRate,
    maxCombo,
  };

  // Free WASM-side resources eagerly so we don't leak across popup reopens.
  bmap.free?.(); attrs.free?.(); attrsBuilder.free?.();
  baseDiff.free?.(); perf.free?.();

  return result;
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
