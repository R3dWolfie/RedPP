# RedPP Privacy Policy

*Last updated: 2026-04-29*

RedPP is a browser extension that calculates osu! performance points
(pp) for beatmaps. It is designed to be entirely client-side.

## Data we collect

**None.** RedPP does not collect, transmit, or store any personal
information, telemetry, analytics, usage data, or identifiers about
the user.

## Data we send

When you open the extension popup on an `osu.ppy.sh` beatmap page, RedPP
makes two kinds of network requests, both directly from your browser to
servers operated by ppy Pty Ltd (the company behind osu!):

1. `GET https://osu.ppy.sh/osu/<beatmap-id>` — fetches the raw `.osu`
   file for the beatmap currently shown in the active tab. This is an
   anonymous request and does not require login.
2. `GET https://assets.ppy.sh/beatmaps/<set-id>/covers/cover@2x.jpg` —
   fetches the beatmap's cover image for display in the popup.

No request is ever sent to any other server. There is no backend
operated by RedPP.

## Data we store

RedPP uses the browser's **session storage** (cleared when the browser
closes) to cache the bytes of `.osu` files it has already fetched, keyed
by beatmap ID. This is a performance optimization to avoid re-fetching
the same file on every popup open.

We do not use cookies, local storage, sync storage, or `IndexedDB`.

## Permissions

RedPP requests the following permissions in its manifest:

| Permission | Why we need it |
|---|---|
| `activeTab` | To read the URL of the active tab and detect the beatmap ID when you click the toolbar icon. |
| `storage` | To cache fetched `.osu` files in `chrome.storage.session` (cleared on browser close). |
| Host permission for `osu.ppy.sh` | To fetch `.osu` files from `osu.ppy.sh/osu/<id>`. |
| Host permission for `assets.ppy.sh` | To load the beatmap cover image. |

## Third-party services

RedPP does not use any third-party SDKs, analytics, ad networks, error
trackers, or external libraries that talk to remote servers. The pp
calculation runs entirely inside your browser as a WebAssembly module
([rosu-pp-js](https://github.com/MaxOhn/rosu-pp-js), MIT licensed,
bundled with the extension).

## Source code

RedPP is open source under the MIT license:
<https://github.com/R3dWolfie/RedPP>. You can audit the source of every
network request and storage operation in `redpp_ext/popup/`.

## Contact

For questions about this policy, open an issue at
<https://github.com/R3dWolfie/RedPP/issues>.
