#!/usr/bin/env bash
# scripts/setup.sh — EduIG-Pipeline Linux/Mac Setup Script
# Usage:  bash scripts/setup.sh
# Requires: Python 3.10+ on PATH
# Idempotent: safe to run multiple times

set -euo pipefail

# ── Color helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; NC='\033[0m'

info()    { echo -e "  ${CYAN}[INFO]${NC}  $1"; }
success() { echo -e "  ${GREEN}[ OK ]${NC}  $1"; }
warn()    { echo -e "  ${YELLOW}[WARN]${NC}  $1"; }
err()     { echo -e "  ${RED}[FAIL]${NC}  $1"; exit 1; }

echo ""
echo -e "${MAGENTA}==========================================${NC}"
echo -e "${MAGENTA}  EduIG-Pipeline — Environment Setup${NC}"
echo -e "${MAGENTA}==========================================${NC}"
echo ""

# ── Step 1: Find Python 3.10+ ────────────────────────────────────────────────
info "Searching for Python 3.10+..."
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            success "Found Python $version at $(command -v "$cmd")"
            break
        fi
    fi
done
[ -z "$PYTHON_CMD" ] && err "Python 3.10+ not found. Install from https://python.org"

# ── Step 2: Create virtual environment ───────────────────────────────────────
if [ ! -d "venv" ]; then
    info "Creating virtual environment at ./venv ..."
    "$PYTHON_CMD" -m venv venv
    success "Virtual environment created"
else
    warn "Virtual environment already exists — skipping creation"
fi

# ── Step 3: Activate virtual environment ─────────────────────────────────────
info "Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate
success "Virtual environment activated (Python: $(python --version))"

# ── Step 4: Upgrade pip ───────────────────────────────────────────────────────
info "Upgrading pip..."
pip install --upgrade pip --quiet
success "pip upgraded to $(pip --version | awk '{print $2}')"

# ── Step 5: Install dependencies ─────────────────────────────────────────────
info "Installing dependencies from requirements.txt (pinned versions)..."
pip install -r requirements.txt --quiet
success "All dependencies installed"

# ── Step 6: Install Playwright Chromium ──────────────────────────────────────
info "Installing Playwright Chromium browser..."
playwright install chromium
success "Playwright Chromium installed"

# ── Step 7: Create data directories ──────────────────────────────────────────
info "Ensuring data directories exist..."
mkdir -p data/raw data/processed data/logs
success "Data directories ready"

# ── Step 8: Copy .env template if not present ────────────────────────────────
if [ ! -f "config/.env" ]; then
    if [ -f "config/.env.example" ]; then
        cp config/.env.example config/.env
        warn "Created config/.env from template — EDIT THIS FILE before running the pipeline!"
    fi
else
    info "config/.env already exists — skipping"
fi

# ── Step 9: Run health check ─────────────────────────────────────────────────
echo ""
info "Running health check..."
echo ""
python scripts/health_check.py || err "Health check failed. Fix the issues above and re-run setup."

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo "  Next steps:"
echo "    1. Edit config/.env  (add Instagram OAuth token if needed)"
echo "    2. Edit config/targets.csv  (add your research targets)"
echo "    3. Run: python run.py --dry-run"
echo ""
