# scripts/setup.ps1 — EduIG-Pipeline Windows Setup Script
# Usage:  .\scripts\setup.ps1
# Requires: Python 3.10+ on PATH, PowerShell 5+
# Idempotent: safe to run multiple times

$ErrorActionPreference = "Stop"

# ── Helpers ──────────────────────────────────────────────────────────────────
function Write-Info    { param($msg) Write-Host "  [INFO]  $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "  [ OK ]  $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "  [WARN]  $msg" -ForegroundColor Yellow }
function Write-Err     { param($msg) Write-Host "  [FAIL]  $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host "  EduIG-Pipeline — Environment Setup" -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host ""

# ── Step 1: Check Python version ─────────────────────────────────────────────
Write-Info "Checking Python version..."
try {
    $pyVersion = python --version 2>&1
    if ($pyVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -ge 3 -and $minor -ge 10) {
            Write-Success "Found $pyVersion"
        } else {
            Write-Err "Python 3.10+ required. Found: $pyVersion. Download from https://python.org"
        }
    } else {
        Write-Err "Could not parse Python version: $pyVersion"
    }
} catch {
    Write-Err "Python not found. Install from https://python.org and add to PATH."
}

# ── Step 2: Create virtual environment ───────────────────────────────────────
if (-not (Test-Path "venv")) {
    Write-Info "Creating virtual environment at ./venv ..."
    python -m venv venv
    Write-Success "Virtual environment created"
} else {
    Write-Warn "Virtual environment already exists — skipping creation"
}

# ── Step 3: Activate virtual environment ─────────────────────────────────────
Write-Info "Activating virtual environment..."
$activateScript = "venv\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Err "Activation script not found: $activateScript. Delete ./venv and re-run."
}
& $activateScript
Write-Success "Virtual environment activated"

# ── Step 4: Upgrade pip ───────────────────────────────────────────────────────
Write-Info "Upgrading pip..."
python -m pip install --upgrade pip --quiet
Write-Success "pip upgraded"

# ── Step 5: Install dependencies ─────────────────────────────────────────────
Write-Info "Installing dependencies from requirements.txt (pinned versions)..."
pip install -r requirements.txt --quiet
Write-Success "All dependencies installed"

# ── Step 6: Install Playwright Chromium browser ───────────────────────────────
Write-Info "Installing Playwright Chromium browser..."
playwright install chromium
Write-Success "Playwright Chromium installed"

# ── Step 7: Create data directories ──────────────────────────────────────────
Write-Info "Ensuring data directories exist..."
$dirs = @("data\raw", "data\processed", "data\logs")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Success "Created $dir"
    }
}
Write-Success "Data directories ready"

# ── Step 8: Copy .env template if not present ────────────────────────────────
if (-not (Test-Path "config\.env")) {
    if (Test-Path "config\.env.example") {
        Copy-Item "config\.env.example" "config\.env"
        Write-Warn "Created config\.env from template — EDIT THIS FILE before running the pipeline!"
    }
} else {
    Write-Info "config\.env already exists — skipping"
}

# ── Step 9: Run health check ─────────────────────────────────────────────────
Write-Host ""
Write-Info "Running health check..."
Write-Host ""
python scripts\health_check.py
if ($LASTEXITCODE -ne 0) {
    Write-Err "Health check failed. Fix the issues above and re-run setup."
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    1. Edit config\.env (add Instagram OAuth token if needed)" -ForegroundColor White
Write-Host "    2. Edit config\targets.csv (add your research targets)" -ForegroundColor White
Write-Host "    3. Run: python run.py --dry-run" -ForegroundColor White
Write-Host ""
