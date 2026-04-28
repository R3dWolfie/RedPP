/* Beatmap acquisition: pull a beatmap ID from the active tab's URL,
   fetch the .osu file from osu's CDN, cache by ID in session storage. */

const SESSION = (typeof browser !== "undefined" && browser.storage?.session)
  ? browser.storage.session
  : (typeof chrome !== "undefined" && chrome.storage?.session)
  ? chrome.storage.session
  : null;

/** Extract beatmap (difficulty) ID from a URL.
 *  Supports:
 *    /b/<id>           → osu! legacy
 *    /beatmaps/<id>    → osu! lazer/web
 *    /beatmapsets/<setid>#<mode>/<id>  → set page with diff selected
 */
export function extractBeatmapId(url) {
  let u;
  try { u = new URL(url); } catch { return null; }
  if (!/(?:^|\.)osu\.ppy\.sh$/.test(u.hostname)) return null;
  let m = u.pathname.match(/^\/(?:b|beatmaps)\/(\d+)/);
  if (m) return parseInt(m[1], 10);
  m = u.hash.match(/\/(\d+)$/);
  if (m && /^\/beatmapsets\//.test(u.pathname)) return parseInt(m[1], 10);
  return null;
}

/** Set ID from a beatmapsets URL (used for the cover image). */
export function extractSetId(url) {
  let u;
  try { u = new URL(url); } catch { return null; }
  const m = u.pathname.match(/^\/beatmapsets\/(\d+)/);
  return m ? parseInt(m[1], 10) : null;
}

/** Fetch the raw .osu bytes for a beatmap ID. Returns Uint8Array. */
export async function fetchOsuBytes(id) {
  const cacheKey = `osu_${id}`;
  if (SESSION) {
    const cached = await SESSION.get(cacheKey);
    if (cached[cacheKey]) {
      return _b64decode(cached[cacheKey]);
    }
  }
  const res = await fetch(`https://osu.ppy.sh/osu/${id}`, { credentials: "omit" });
  if (!res.ok) throw new Error(`osu.ppy.sh returned ${res.status}`);
  const buf = new Uint8Array(await res.arrayBuffer());
  if (buf.byteLength < 16 || !_looksLikeOsu(buf)) {
    throw new Error("response does not look like a .osu file");
  }
  if (SESSION) {
    await SESSION.set({ [cacheKey]: _b64encode(buf) }).catch(() => {});
  }
  return buf;
}

/** Pull set ID out of the .osu file's [Metadata] section, if present.
 *  Falls back to URL-parsed setId. */
export function extractSetIdFromOsu(bytes) {
  const text = new TextDecoder("utf-8").decode(bytes.slice(0, 4096));
  const m = text.match(/^BeatmapSetID\s*:\s*(\d+)/m);
  return m ? parseInt(m[1], 10) : null;
}

export function coverUrl(setId) {
  return `https://assets.ppy.sh/beatmaps/${setId}/covers/cover@2x.jpg`;
}

// --- helpers --------------------------------------------------------
function _looksLikeOsu(buf) {
  // First non-BOM bytes should start with "osu file format"
  const head = new TextDecoder("utf-8").decode(buf.slice(0, 32));
  return /^osu file format/.test(head.trim());
}

function _b64encode(u8) {
  let s = "";
  const chunk = 0x8000;
  for (let i = 0; i < u8.length; i += chunk) {
    s += String.fromCharCode.apply(null, u8.subarray(i, i + chunk));
  }
  return btoa(s);
}

function _b64decode(b64) {
  const s = atob(b64);
  const u8 = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) u8[i] = s.charCodeAt(i);
  return u8;
}
