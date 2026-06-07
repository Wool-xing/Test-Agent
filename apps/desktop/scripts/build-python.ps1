# Build Python backend with PyInstaller (Windows PowerShell)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "Building Python backend..."
pip install pyinstaller -q
pyinstaller --clean --noconfirm pyinstaller/tagent_backend.spec
Write-Host "Backend built: dist-python/tagent-backend.exe"
