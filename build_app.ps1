$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& .\.venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed --name redpp `
    --add-data "redpp_app/theme.qss;redpp_app" `
    --add-data "redpp_app/assets;redpp_app/assets" `
    --hidden-import=PySide6 `
    --hidden-import=rosu_pp_py `
    _launch.py
Write-Output "binary at: dist/redpp.exe"
