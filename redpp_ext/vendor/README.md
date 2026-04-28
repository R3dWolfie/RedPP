# Vendored third-party files

This directory contains a pre-compiled WebAssembly module that is
**not** built from source as part of this extension's build pipeline.
The files here are vendored verbatim from a public, MIT-licensed
upstream release.

## `rosu_pp_js.js`, `rosu_pp_js_bg.wasm`

- **Upstream project:** [`MaxOhn/rosu-pp-js`](https://github.com/MaxOhn/rosu-pp-js)
- **Upstream version:** `v4.0.1` (release date 2026-04-12)
- **License:** MIT (see `LICENSE.rosu-pp-js`)
- **Source artifact:** [`rosu_pp_js_web.tar.gz`](https://github.com/MaxOhn/rosu-pp-js/releases/download/v4.0.1/rosu_pp_js_web.tar.gz)
  from the upstream's GitHub Release page.
- **Build target:** `web` (one of three targets the upstream publishes;
  the others are `nodejs` and `bundler`).

## How to reproduce

To verify the bundled WASM matches the upstream release:

```bash
# In a fresh directory:
curl -sLO https://github.com/MaxOhn/rosu-pp-js/releases/download/v4.0.1/rosu_pp_js_web.tar.gz
tar xzf rosu_pp_js_web.tar.gz
sha256sum rosu_pp_js_bg.wasm rosu_pp_js.js
```

Compare those checksums against the files in this directory. They
should be byte-identical.

To build from source instead (requires Rust + `wasm-pack`):

```bash
git clone https://github.com/MaxOhn/rosu-pp-js
cd rosu-pp-js
git checkout v4.0.1
wasm-pack build --target web --release
# Output is in pkg/
```

## Why vendored, not built in CI

Manifest v3 disallows remote code execution, and reproducibly building a
Rust→WASM toolchain inside the extension's CI pipeline adds significant
maintenance burden for a small dependency. Pinning to an upstream
release tag is simpler, equally auditable, and the upstream artifact
is well-known in the osu! ecosystem (it's the same library used by
osu!lazer for pp calculation).

## What we changed

Nothing. The files are byte-identical to the upstream release. RedPP
imports `rosu_pp_js.js` as an ES module from inside the popup; no
patching, no minification, no transformation.
