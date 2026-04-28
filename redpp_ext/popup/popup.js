/* Popup main: pull beatmap from the active tab, fetch + calc on each
   slider/chip change, render. Strict scope: what's this map worth at
   <acc>% with <mods>? */

import { extractBeatmapId, extractSetId, fetchOsuBytes,
         extractSetIdFromOsu, coverUrl } from "./beatmap.js";
import { compute, readMetadata } from "./calc.js";

const $ = (id) => document.getElementById(id);

const RANK_COLORS = {
  SS: "#FFD370", S: "#5BD7E0", A: "#88C540",
  B:  "#5DADE2", C: "#B47BC9", D: "#E74C3C",
};

const ALL_MODS = ["HD", "HR", "DT", "FL", "EZ", "HT", "NC", "BL"];

// In-popup state ----------------------------------------------------
const state = {
  osuBytes: null,
  meta: { artist: "", title: "", version: "", setId: null },
  activeMods: new Set(),
  accuracy: 100.0,
  baseStars: 0.0,
};

// --- helpers -------------------------------------------------------
function computeRank(acc) {
  if (acc >= 100.0) return "SS";
  if (acc >=  95.0) return "S";
  if (acc >=  90.0) return "A";
  if (acc >=  80.0) return "B";
  if (acc >=  70.0) return "C";
  return "D";
}

function formatPp(pp) {
  if (pp >= 1_000_000) return `${(pp / 1_000_000).toFixed(1)}M`;
  if (pp >=   100_000) return `${(pp / 1_000).toFixed(0)}K`;
  if (pp >=    10_000) return Math.round(pp).toLocaleString("en-US");
  return Math.round(pp).toString();
}

function setStatus(msg, isError = false) {
  const el = $("status");
  el.textContent = msg || "";
  el.classList.toggle("error", !!isError);
}

function renderBadge(rank) {
  const b = $("badge");
  b.textContent = rank;
  b.style.background = RANK_COLORS[rank] || RANK_COLORS.D;
  b.style.fontSize = rank.length === 1 ? "22pt" : "16pt";
}

function renderSliderFill() {
  const s = $("acc-slider");
  const pct = ((s.value - s.min) / (s.max - s.min)) * 100;
  s.style.setProperty("--fill", `${pct}%`);
}

function setActiveMods() {
  for (const btn of document.querySelectorAll(".chip")) {
    btn.classList.toggle("active", state.activeMods.has(btn.dataset.mod));
  }
}

function effectiveMods() {
  // Preserve canonical order (ALL_MODS order) so the string is stable.
  return ALL_MODS.filter((m) => state.activeMods.has(m)).join("");
}

// --- main render loop ---------------------------------------------
async function recompute() {
  if (!state.osuBytes) return;
  try {
    const r = await compute(state.osuBytes, effectiveMods(), state.accuracy);
    $("stars").textContent = r.stars.toFixed(2);
    $("chevron").hidden = !(r.stars > state.baseStars + 0.05);
    $("stats").textContent =
      `AR ${r.ar.toFixed(1)} · OD ${r.od.toFixed(1)} · CS ${r.cs.toFixed(1)} · HP ${r.hp.toFixed(1)} · BPM ${Math.round(r.bpm)}`;
    const rank = computeRank(state.accuracy);
    renderBadge(rank);
    $("pp-text").textContent =
      `${formatPp(r.pp)}pp for ${state.accuracy.toFixed(1)}%`;
  } catch (e) {
    setStatus(`calc failed: ${e.message}`, true);
  }
}

function renderHero(setIdFallback) {
  $("artist").textContent = state.meta.artist
    ? `[${state.meta.artist}]` : "";
  $("title").textContent = state.meta.title || "—";
  $("diff").textContent = state.meta.version || "";
  const sid = state.meta.setId || setIdFallback;
  if (sid) {
    $("hero").querySelector(".hero-bg").style.backgroundImage =
      `url("${coverUrl(sid)}")`;
  }
}

// --- bootstrap -----------------------------------------------------
async function bootstrap() {
  setStatus("loading…");
  // Footer pulls version from the manifest so it never drifts.
  try {
    const v = chrome.runtime.getManifest().version;
    $("footer").textContent = `RedPP v${v}`;
  } catch { /* dev environment without runtime — leave default */ }
  // Initial defaults: slider = 100%, no mods, default badge.
  $("acc-val").textContent = "100.0";
  renderSliderFill();
  renderBadge("D");

  let tab;
  try {
    [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  } catch {
    setStatus("can't read active tab", true); return;
  }
  if (!tab?.url) { setStatus("no active tab URL", true); return; }

  const id = extractBeatmapId(tab.url);
  if (!id) {
    setStatus(
      "open a specific beatmap difficulty (e.g. /b/<id> or " +
      "select a diff on a beatmapset page).", true);
    return;
  }
  const setIdFromUrl = extractSetId(tab.url);

  let bytes;
  try {
    bytes = await fetchOsuBytes(id);
  } catch (e) {
    setStatus(`fetch failed: ${e.message}`, true); return;
  }
  state.osuBytes = bytes;
  state.meta = readMetadata(bytes);
  if (!state.meta.setId && setIdFromUrl) state.meta.setId = setIdFromUrl;

  // Get base stars (no mods) once for the chevron decision.
  try {
    const base = await compute(bytes, "", 100.0);
    state.baseStars = base.baseStars;
  } catch { /* ignore — non-fatal */ }

  renderHero(setIdFromUrl);
  setStatus("");
  await recompute();
}

// --- wiring --------------------------------------------------------
function wireEvents() {
  for (const btn of document.querySelectorAll(".chip")) {
    btn.addEventListener("click", () => {
      const m = btn.dataset.mod;
      if (state.activeMods.has(m)) state.activeMods.delete(m);
      else state.activeMods.add(m);
      setActiveMods();
      recompute();
    });
  }
  const slider = $("acc-slider");
  slider.addEventListener("input", () => {
    // Slider is 0..1000 ticks at 0.1% step.
    state.accuracy = parseInt(slider.value, 10) / 10.0;
    $("acc-val").textContent = state.accuracy.toFixed(1);
    renderSliderFill();
    recompute();
  });
}

// --- go ------------------------------------------------------------
wireEvents();
bootstrap().catch((e) => setStatus(`init failed: ${e.message}`, true));
