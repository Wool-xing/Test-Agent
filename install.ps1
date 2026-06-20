# Test-Agent V2.0.0 — one-command install (Windows PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "Test-Agent V2.0.0 — Install" -ForegroundColor Cyan

# Detect Python
$python = $null
foreach ($cmd in @("python", "python3")) {
    try {
        $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        $major = & $cmd -c "import sys; print(sys.version_info.major)" 2>$null
        if ($major -ge 3) {
            $python = $cmd
            Write-Host "  Python $ver ($cmd)" -ForegroundColor Green
            break
        }
    } catch {}
}
if (-not $python) {
    Write-Host "Python >= 3.10 required. Install from https://python.org" -ForegroundColor Red
    exit 1
}

# Install
Write-Host "`nInstalling dependencies..."
& $python -m pip install --upgrade pip -q
& $python -m pip install -r requirements/base.txt -q 2>$null
if ($LASTEXITCODE -ne 0) {
    & $python -m pip install -e . -q 2>$null
}

# Quick test
Write-Host "`nVerifying..."
& $python -m runtime.cli.main --version 2>$null
if ($LASTEXITCODE -ne 0) {
    & $python -c "from runtime import __version__; print(f'Test-Agent v{__version__}')"
}

Write-Host "`nInstall complete." -ForegroundColor Green
Write-Host "Next: tagent init or see STARTUP.md" -ForegroundColor Cyan
