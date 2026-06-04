# Antigravity Session Handoff Document

**Hello Antigravity!** 👋
If you are reading this, you have been instantiated in a new session to continue work on the **EduIG-Pipeline** project. The previous agent successfully built the foundational architecture and completed Phases 1 through 5 (Tasks 1-22). 

This document serves as your complete context-restoration map. Read it carefully before executing any new tasks.

---

## 1. Project Overview
**EduIG-Pipeline** is a privacy-first, ethically engineered Instagram data scraper designed exclusively for academic and institutional research. It securely extracts public data, mathematically anonymizes personal identifiers, strictly strips out PII (Emails, Phone Numbers, Links), and stores normalized data in an ACID-compliant local SQLite database.

## 2. Technology Stack & Constraints
You must strictly adhere to the following tools and rules. **Do not deviate** from this stack without explicit user permission:
*   **Python Version**: 3.14+ (We are leveraging modern `X | None` syntax instead of `Optional[X]`).
*   **Browser Extraction**: `playwright` (Specifically `sync_playwright` with Chromium).
*   **API Extraction**: `httpx` (Asynchronous engine inside a synchronous wrapper. **Do not use `requests`**).
*   **Data Validation**: `pydantic` (v2).
*   **Logging**: `structlog` (Outputting JSON lines). **CRITICAL RULE: No `print()` statements are allowed anywhere in the codebase.**
*   **Typing**: Strict static typing is enforced. `mypy src/ --strict` currently passes with 0 errors. Keep it that way.
*   **Testing**: `pytest` with `pytest-cov`. Current coverage is **94%**. You must keep coverage strictly above **80%**.
*   **Formatting**: `black` and `isort` configured for 100-character line lengths.

---

## 3. Core Architecture & File Structure
The project is built on a modular, decoupled architecture:

*   **`run.py`**: The main orchestrator. Parses CLI args (`--dry-run`, `--resume`, `--export-csv`), loads targets, spins up workers, and orchestrates the extraction -> normalization -> storage pipeline.
*   **`config/targets.csv`**: Target ingestion file. Format: `[URL], [Consent_Boolean]`.
*   **`src/config_loader.py`**: Pydantic-based `settings.yaml` and `.env` loader.
*   **`src/browser_worker.py`**: Uses Playwright to inject Javascript and grab unauthenticated public JSON payloads.
*   **`src/api_worker.py`**: Uses `httpx` to ping the official Facebook Graph API for *consented* users (requires `EDUIG_API__ACCESS_TOKEN`).
*   **`src/router.py`**: Decides whether to route the target to the BrowserWorker or APIWorker based on consent and token availability.
*   **`src/normalizer.py`**: Standardizes payloads into `ProfileSchema` and `PostSchema`. Hashes usernames with SHA-256 for anonymity.
*   **`src/compliance.py`**: The ethical core. Contains `PIIStripper` (regexes away emails/phones/linktrees from bios), `ConsentTracker`, and `AuditGenerator`.
*   **`src/storage.py`**: SQLite wrapper utilizing WAL-mode for thread-safe concurrent writes. Database lives at `data/eduig.db`.
*   **`data/exports/`**: Generated CSV dumps live here.

---

## 4. Current State (What's Done)
The initial 22-Task spec from the user (`PROMPT_FOR_ANTIGRAVITY.md`) is **100% Complete**.
*   The dual-engine extraction system works.
*   The database successfully writes and enforces schemas.
*   The compliance engine successfully generates IRB-ready audit reports.
*   Code is completely formatted, strictly typed, and thoroughly tested.

You can verify the system's operational status by running:
```bash
venv\Scripts\python.exe run.py --export-csv
```
This will extract data for the profiles listed in `config/targets.csv` and dump the resulting SQLite records into `data/exports/profiles_export.csv`.

---

## 5. Your Directives for This Session
Since the core pipeline is completely hardened, your role in this new session will be to expand the feature set based on the user's new instructions. 

**Before writing new code:**
1. Run `venv\Scripts\pytest.exe tests/ -v --cov=src` to ensure the environment is healthy.
2. If introducing new files, ensure they are typed, tested, and added to the `black`/`isort` standard.
3. If altering database schemas, ensure you migrate `data/eduig.db` smoothly without data loss (or ask the user if a DB wipe is acceptable).

Good luck, and build awesome things! 🚀
