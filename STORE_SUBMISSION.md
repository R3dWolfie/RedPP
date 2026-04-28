# Store Submission Guide — Chrome Web Store + Firefox AMO

Everything you need to copy-paste into the submission forms. Both
stores will ask broadly the same questions; the field names differ.

---

## 1. Required artifacts (already built by CI)

After tag `v0.2.0` finishes building, grab these from the
[GitHub release](https://github.com/R3dWolfie/RedPP/releases/tag/v0.2.0):

| File | Goes to |
|---|---|
| `RedPP-chrome-0.2.0.zip` | Chrome Web Store |
| `RedPP-firefox-0.2.0.zip` | Firefox AMO |

Both contain identical code; the manifest's `browser_specific_settings`
block is honoured by Firefox and ignored by Chrome.

---

## 2. Listing copy (fill into both stores)

### Name
```
RedPP — osu! pp calculator
```

### Short description (132 char max — Chrome's "Summary")
```
What is this map worth? Live pp calculation for any osu!(lazer) beatmap, right from the toolbar. Adjust mods + accuracy.
```

### Full description (long form)
```
RedPP is a click-the-toolbar pp calculator for osu! beatmaps.

Open any beatmap page on osu.ppy.sh, click the RedPP icon, and you'll
see a clean popup with:

  • Star rating + AR / OD / CS / HP / BPM (mod-adjusted live)
  • 8 mod chips (HD, HR, DT, FL, EZ, HT, NC, BL) — toggle any
    combination to see what-if pp
  • Accuracy slider from 0% to 100%, full granularity
  • Rank-by-accuracy badge (D / C / B / A / S / SS) updates as you
    drag, matching osu!lazer's grading thresholds

Calculation runs entirely client-side via the official rosu-pp library
compiled to WebAssembly — the same algorithm osu!lazer itself uses for
performance points. No backend, no API key, no login required.

How it works:
  1. Open any beatmap page (osu.ppy.sh/b/123, /beatmaps/123, or a
     beatmapset page with a difficulty selected).
  2. Click the RedPP toolbar icon.
  3. Drag the accuracy slider, click mods, see pp update in real time.

Permissions explained:
  • activeTab — to read the URL of the active tab so we can detect the
    beatmap ID.
  • storage — to cache fetched .osu files in your session (cleared on
    browser close).
  • osu.ppy.sh / assets.ppy.sh — to download the beatmap and its cover
    image.

Open source under the MIT license. Source code, issue tracker, and
release downloads at https://github.com/R3dWolfie/RedPP

If you also want a desktop overlay that calculates pp live during
gameplay (with tosu integration), grab the desktop app from the same
GitHub releases page.
```

### Category
- **Chrome Web Store:** *Productivity* (closest match — they don't have
  a games category for extensions). Alternative: *Tools*.
- **Firefox AMO:** *Other → Web Development* or
  *Other → Search Tools*. AMO categorization is loose; pick the closest.

### Language
English (US).

---

## 3. Privacy practices

Both stores ask about data handling. Use these answers:

| Question | Answer |
|---|---|
| Do you collect personal/personally identifiable info? | **No** |
| Do you collect health/financial info? | **No** |
| Do you collect authentication info? | **No** |
| Do you collect web history? | **No** |
| Do you collect user activity? | **No** |
| Do you collect website content? | **Yes** — read-only, fetches the `.osu` file for the beatmap currently in the active tab. Used solely for pp calculation in the popup. Never transmitted off-device. |
| Do you sell/share user data with third parties? | **No** |
| Do you use data for unrelated purposes? | **No** |
| Do you use data to determine creditworthiness? | **No** |

**Privacy policy URL:** point both stores at the live file in the repo:
```
https://github.com/R3dWolfie/RedPP/blob/master/PRIVACY.md
```

(Or copy `PRIVACY.md` into a GitHub Pages site and use that URL — looks
slightly more polished, not required.)

---

## 4. Permissions justification (Chrome only)

Chrome Web Store reviewers ask for a one-line justification per
permission. Paste these directly:

- **activeTab:** "Read the URL of the active tab to detect which osu!
  beatmap is being viewed. The popup never injects scripts into pages."
- **storage:** "Cache previously fetched `.osu` files in
  `chrome.storage.session` so reopening the popup is instant. Cleared
  when the browser closes."
- **Host permission `https://osu.ppy.sh/*`:** "Download the `.osu`
  beatmap file from osu's anonymous CDN endpoint
  `osu.ppy.sh/osu/<id>`. Required to calculate pp."
- **Host permission `https://assets.ppy.sh/*`:** "Load the beatmap's
  cover image for display in the popup hero strip."

---

## 5. Screenshots

Both stores require screenshots. Capture these manually from the live
extension. Recommended specs:

- Chrome: 1280 × 800 OR 640 × 400 PNG. Up to 5 images.
- Firefox: any size, up to 10 images.

Suggested shots (click the toolbar icon on each):

1. Popup open over a beatmap page, default 100% / no mods — shows the
   "what is this map worth at 100% no mods" baseline. **Best hero shot.**
2. Same popup with HD + HR + DT chips active — demonstrates the mod
   override mechanic and the gold-lit chips.
3. Slider dragged to 90% — shows the rank badge changing from SS to A.

Save them as `store-screenshots/01.png` etc. Don't commit huge PNGs to
the repo unless you want; they're for the upload form only.

---

## 6. Promo tile / icon (Chrome only)

Chrome Web Store requires a 440 × 280 promo tile and a 128 × 128 icon.
The 128px is already in `redpp_ext/icons/icon128.png`. For a 440×280
tile, you can either:

- Generate a quick one with ImageMagick by combining the icon + the
  app name on a brand-coloured background, or
- Skip the small tile (it's optional in the new dashboard) and just
  use the 128×128.

Quick command for a placeholder tile:
```bash
magick -size 440x280 xc:'#1A2333' \
  \( redpp_ext/icons/icon128.png -resize 200x200 \) -gravity center -geometry +-110+0 -composite \
  -font DejaVu-Sans-Bold -pointsize 48 -fill '#FFFFFF' \
  -gravity east -annotate +50+0 "RedPP" \
  store-promo-440x280.png
```

---

## 7. Submission flow

### Chrome Web Store

1. Sign in at <https://chrome.google.com/webstore/devconsole> with the
   Google account you want associated with the listing.
2. Pay the **$5 one-time developer registration fee** (only once per
   account, ever).
3. Click **New item**, drag in `RedPP-chrome-0.2.0.zip`.
4. Fill in the form:
   - Listing → paste short + long description from §2.
   - Privacy → upload screenshots, paste privacy URL from §3, declare
     practices.
   - Permissions justification → paste from §4.
5. Click **Submit for review**. First-submission review usually takes
   1–3 business days.

### Firefox AMO (addons.mozilla.org)

1. Sign in at <https://addons.mozilla.org/en-US/developers/> (free —
   uses your Firefox account).
2. Click **Submit a new add-on**, pick **On this site**, upload
   `RedPP-firefox-0.2.0.zip`. AMO will run an automated linter — should
   pass clean.
3. Pick distribution: **Listed on this website**.
4. Fill in the form:
   - Name, summary, full description from §2.
   - Categories.
   - Privacy URL from §3.
   - Source code URL: `https://github.com/R3dWolfie/RedPP` (Mozilla
     reviewers may ask for this; you can supply it preemptively).
5. Submit. AMO automated review usually completes in minutes; human
   review (if triggered) usually <24 h.

---

## 8. After publish

Bump versions through normal git tags. Each tag push will rebuild both
zips through CI. The store-submission flow for updates is much shorter —
just upload the new zip, no re-fill of the form fields.

For Chrome, you may want to enable the **publish on accept** option so
updates go live as soon as review passes. For AMO, updates auto-publish
unless flagged.
