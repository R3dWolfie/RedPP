# Third-Party Notices

RedPP is MIT-licensed (see [LICENSE](LICENSE)). It bundles or depends on
the following third-party software, each retaining its own license:

| Component       | License           | Project                                              |
|-----------------|-------------------|------------------------------------------------------|
| rosu-pp-py      | MIT               | https://github.com/MaxOhn/rosu-pp-py                 |
| rosu-pp-js      | MIT (vendored under `redpp_ext/vendor/`) | https://github.com/MaxOhn/rosu-pp-js |
| rosu-pp         | MIT               | https://github.com/MaxOhn/rosu-pp                    |
| PySide6 (Qt 6)  | LGPL v3           | https://www.qt.io/qt-for-python                      |
| PyInstaller     | GPL v2 (with exception for bundled apps) | https://pyinstaller.org   |
| tosu (runtime)  | GPL v3            | https://github.com/tosuapp/tosu — *not bundled, runs as a separate process* |

## Qt / PySide6 (LGPL)

Distributed binaries (`redpp.exe`, `redpp` ELF, AppImage) bundle PySide6
and the underlying Qt libraries. Per LGPL v3, you have the right to
replace those Qt libraries with your own build. PyInstaller `--onefile`
extracts to `$TMPDIR/_MEIxxxxx/` at runtime; the Qt `.so` / `.dll` files
in that directory may be substituted with compatible builds of the same
version.

## tosu

tosu is **not** bundled with RedPP. RedPP communicates with tosu over
HTTP (`127.0.0.1:24050`) when the user has installed and started it
separately. tosu's GPL v3 license therefore does not apply to RedPP's
own distribution.
