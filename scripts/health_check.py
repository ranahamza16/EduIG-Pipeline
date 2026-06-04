#!/usr/bin/env python3
"""Health check script for EduIG-Pipeline.

Verifies that all required dependencies are installed and importable.
Run this after setup to confirm the environment is ready.

Usage:
    python scripts/health_check.py
"""

import os
import sys

# Force UTF-8 output on Windows terminals that default to cp1252
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]


def check_python_version() -> bool:
    """Verify Python 3.10+ is being used."""
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 10:
        print(f"  [OK]  Python {major}.{minor}.{sys.version_info[2]}")
        return True
    print(f"  [FAIL] Python {major}.{minor} -- need 3.10+ (upgrade at https://python.org)")
    return False


def check_import(module: str, display_name: str | None = None) -> bool:
    """Try to import a module and report status."""
    name = display_name or module
    try:
        __import__(module)
        print(f"  [OK]  {name}")
        return True
    except ImportError as e:
        print(f"  [FAIL] {name}: {e}")
        return False


def check_pydantic_version() -> bool:
    """Verify Pydantic v2 is installed (not v1)."""
    try:
        import pydantic
        version = pydantic.VERSION
        if version.startswith("2."):
            print(f"  [OK]  pydantic v{version}")
            return True
        print(f"  [FAIL] pydantic v{version} -- need v2.x (pip install 'pydantic>=2.0.0')")
        return False
    except ImportError:
        print("  [FAIL] pydantic -- not installed")
        return False


def check_playwright() -> bool:
    """Verify Playwright is installed and Chromium browser is available."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        print("  [OK]  playwright (Chromium browser ready)")
        return True
    except ImportError:
        print("  [FAIL] playwright -- not installed (pip install playwright)")
        return False
    except Exception as e:
        if "chromium" in str(e).lower() or "browser" in str(e).lower():
            print("  [FAIL] playwright Chromium not installed (run: playwright install chromium)")
        else:
            print(f"  [FAIL] playwright -- {e}")
        return False


def main() -> int:
    """Run all health checks and return exit code."""
    print("=" * 50)
    print("  EduIG-Pipeline — Environment Health Check")
    print("=" * 50)

    failures: list[str] = []

    # Python version
    print("\n[Python]")
    if not check_python_version():
        failures.append("python_version")

    # Core dependencies
    print("\n[Core Dependencies]")
    core_checks = [
        ("httpx", "httpx"),
        ("structlog", "structlog"),
        ("yaml", "pyyaml"),
        ("dotenv", "python-dotenv"),
        ("schedule", "schedule"),
    ]
    for module, name in core_checks:
        if not check_import(module, name):
            failures.append(name)

    # Pydantic v2 check
    print("\n[Pydantic v2]")
    if not check_pydantic_version():
        failures.append("pydantic_v2")

    # Playwright + browser
    print("\n[Playwright]")
    if not check_playwright():
        failures.append("playwright")

    # Data processing
    print("\n[Data Processing]")
    data_checks = [
        ("pandas", "pandas"),
        ("polars", "polars"),
        ("matplotlib", "matplotlib"),
        ("seaborn", "seaborn"),
    ]
    for module, name in data_checks:
        if not check_import(module, name):
            failures.append(name)

    # Dev tools
    print("\n[Dev Tools]")
    dev_checks = [
        ("pytest", "pytest"),
        ("black", "black"),
        ("mypy", "mypy"),
        ("isort", "isort"),
        ("flake8", "flake8"),
    ]
    for module, name in dev_checks:
        check_import(module, name)  # Dev tools are optional, don't fail

    # Summary
    print("\n" + "=" * 50)
    if not failures:
        print("  [OK]  All checks passed! Ready to run EduIG-Pipeline.")
        print("  Next: edit config/.env and config/targets.csv, then:")
        print("        python run.py --dry-run")
        return 0
    else:
        print(f"  [FAIL] {len(failures)} check(s) failed: {', '.join(failures)}")
        print("  Fix issues above, then re-run: python scripts/health_check.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
