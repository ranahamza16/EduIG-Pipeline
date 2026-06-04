# Bash Scripting Skill
## Production-Ready Shell Scripts for EduIG-Pipeline

---

## Overview

This skill provides patterns for writing robust, cross-platform setup and utility scripts for the EduIG-Pipeline project. On Windows, use **PowerShell**; on Linux/Mac, use **Bash**. All scripts must be idempotent (safe to run multiple times).

---

## Core Rules

- **Always check Python version** before proceeding
- **Always use virtual environments** — never install globally
- **All scripts must be idempotent** — running twice should not cause errors
- **Always provide meaningful output** — use colored output with status indicators
- **Always handle errors** — exit with non-zero code on failure

---

## Pattern 1: Setup Script (Bash/Linux/Mac)

```bash
#!/bin/bash
# scripts/setup.sh - EduIG-Pipeline environment setup
# Usage: bash scripts/setup.sh
# Idempotent: safe to run multiple times

set -euo pipefail  # Exit on error, undefined vars, pipe failure

# --- Color output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Check Python version ---
info "Checking Python version..."
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            success "Found Python $version at $(which $cmd)"
            break
        fi
    fi
done

[ -z "$PYTHON_CMD" ] && error "Python 3.10+ not found. Install from https://python.org"

# --- Create virtual environment ---
if [ ! -d "venv" ]; then
    info "Creating virtual environment..."
    "$PYTHON_CMD" -m venv venv
    success "Virtual environment created at ./venv"
else
    warning "Virtual environment already exists, skipping creation"
fi

# --- Activate virtual environment ---
info "Activating virtual environment..."
source venv/bin/activate
success "Virtual environment activated"

# --- Upgrade pip ---
info "Upgrading pip..."
pip install --upgrade pip --quiet
success "pip upgraded"

# --- Install dependencies ---
info "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --quiet
success "Dependencies installed"

# --- Install Playwright browsers ---
info "Installing Playwright Chromium browser..."
playwright install chromium
success "Playwright Chromium installed"

# --- Create data directories ---
info "Creating data directories..."
mkdir -p data/raw data/processed data/logs
success "Data directories created"

# --- Copy env template if not exists ---
if [ ! -f "config/.env" ]; then
    if [ -f "config/.env.example" ]; then
        cp config/.env.example config/.env
        warning "Created config/.env from template — EDIT THIS FILE before running"
    fi
fi

# --- Run health check ---
info "Running health check..."
python scripts/health_check.py && success "Health check passed" || error "Health check failed"

echo ""
success "Setup complete! Run: python run.py --dry-run"
```

---

## Pattern 2: Setup Script (PowerShell/Windows)

```powershell
# scripts/setup.ps1 - EduIG-Pipeline environment setup (Windows)
# Usage: .\scripts\setup.ps1
# Idempotent: safe to run multiple times

$ErrorActionPreference = "Stop"

function Write-Info    { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "[OK] $args" -ForegroundColor Green }
function Write-Warning { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-Err     { Write-Host "[ERROR] $args" -ForegroundColor Red; exit 1 }

# --- Check Python version ---
Write-Info "Checking Python version..."
try {
    $version = python --version 2>&1
    $versionNum = ($version -replace "Python ", "").Split(".")
    if ([int]$versionNum[0] -ge 3 -and [int]$versionNum[1] -ge 10) {
        Write-Success "Found $version"
    } else {
        Write-Err "Python 3.10+ required. Found: $version"
    }
} catch {
    Write-Err "Python not found. Install from https://python.org"
}

# --- Create virtual environment ---
if (-not (Test-Path "venv")) {
    Write-Info "Creating virtual environment..."
    python -m venv venv
    Write-Success "Virtual environment created"
} else {
    Write-Warning "Virtual environment already exists, skipping"
}

# --- Activate ---
Write-Info "Activating virtual environment..."
& "venv\Scripts\Activate.ps1"
Write-Success "Virtual environment activated"

# --- Install dependencies ---
Write-Info "Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
Write-Success "Dependencies installed"

# --- Playwright ---
Write-Info "Installing Playwright Chromium..."
playwright install chromium
Write-Success "Playwright Chromium installed"

# --- Data directories ---
Write-Info "Creating data directories..."
New-Item -ItemType Directory -Force -Path "data\raw", "data\processed", "data\logs" | Out-Null
Write-Success "Data directories created"

# --- Health check ---
Write-Info "Running health check..."
python scripts\health_check.py
Write-Success "Setup complete! Run: python run.py --dry-run"
```

---

## Pattern 3: Health Check Script

```python
#!/usr/bin/env python3
# scripts/health_check.py - Verify all dependencies are importable

import sys

def check_import(module: str, package_name: str | None = None) -> bool:
    """Try to import a module, print status."""
    try:
        __import__(module)
        print(f"  ✓ {package_name or module}")
        return True
    except ImportError as e:
        print(f"  ✗ {package_name or module}: {e}")
        return False

def main() -> int:
    print("EduIG-Pipeline Health Check")
    print("=" * 40)
    
    # Check Python version
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 10:
        print(f"  ✓ Python {major}.{minor}")
    else:
        print(f"  ✗ Python {major}.{minor} (need 3.10+)")
        return 1
    
    print("\nCore Dependencies:")
    checks = [
        ("playwright.sync_api", "playwright"),
        ("httpx", "httpx"),
        ("pydantic", "pydantic v2"),
        ("structlog", "structlog"),
        ("yaml", "pyyaml"),
        ("dotenv", "python-dotenv"),
        ("schedule", "schedule"),
        ("pandas", "pandas"),
        ("polars", "polars"),
    ]
    
    results = [check_import(mod, name) for mod, name in checks]
    
    print("\nDev Dependencies:")
    dev_checks = [
        ("pytest", "pytest"),
        ("black", "black"),
        ("mypy", "mypy"),
    ]
    [check_import(mod, name) for mod, name in dev_checks]
    
    print("\nPydantic Version Check:")
    import pydantic
    version = pydantic.VERSION
    if version.startswith("2."):
        print(f"  ✓ Pydantic v{version}")
    else:
        print(f"  ✗ Pydantic v{version} (need v2.x)")
        results.append(False)
    
    if all(results):
        print("\n✓ All checks passed!")
        return 0
    else:
        print("\n✗ Some checks failed. Run: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## Pattern 4: Makefile

```makefile
# Makefile - Common commands for EduIG-Pipeline
.PHONY: install test lint format typecheck run clean health-check

install:
	bash scripts/setup.sh

health-check:
	python scripts/health_check.py

test:
	pytest tests/ -v --cov=src --cov-fail-under=80

test-unit:
	pytest tests/ -v -m "not integration" --cov=src

test-integration:
	pytest tests/integration/ -v

lint:
	flake8 src/ --max-line-length=100
	flake8-print src/

format:
	black src/ tests/
	isort src/ tests/

format-check:
	black --check src/ tests/
	isort --check-only src/ tests/

typecheck:
	mypy src/ --strict

run:
	python run.py --config config/settings.yaml

dry-run:
	python run.py --dry-run

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
```

---

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Script not idempotent | Check if resource exists before creating |
| Wrong Python version | Always verify with `python --version` before venv creation |
| Venv not activated | Use absolute paths or check `$VIRTUAL_ENV` env var |
| Windows path separators | Use `os.path.join()` or `pathlib.Path` in Python scripts |
| Playwright not finding browser | Always run `playwright install chromium` after pip install |
| Missing data directories | Create in setup script with `mkdir -p` |

---

**End of Bash Scripting Skill**
