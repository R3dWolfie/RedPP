#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
.venv/bin/pyinstaller --noconfirm --onefile --windowed --name redpp \
    --add-data "redpp_app/theme.qss:redpp_app" \
    --add-data "redpp_app/assets:redpp_app/assets" \
    --hidden-import=PySide6 \
    --hidden-import=rosu_pp_py \
    _launch.py
echo "binary at: dist/redpp"
