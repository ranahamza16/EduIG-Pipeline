# AI_RULES.docx - Non-Negotiable Development Rules
## EduIG-Pipeline: Critical Mandates for AI-Assisted Development

**Version:** 1.0  
**Date:** 2026-05-31  
**Severity:** CRITICAL - Violations require immediate rollback  
**Enforcement:** Automated linting + manual code review  

---

## Rule 1: Python 3.10+ Only

- **Mandate:** All code must use Python 3.10 or higher.
- **Rationale:** Type hinting with `|` union syntax (`str | None`), pattern matching, and improved error messages.
- **Enforcement:** `pyproject.toml` specifies `requires-python = ">=3.10"`. CI fails on lower versions.
- **Forbidden:** `from typing import Optional, Union` (use `| None`, `str | int` instead).

---

## Rule 2: Pydantic v2 for All Data Models

- **Mandate:** Every data structure crossing module boundaries must be a Pydantic `BaseModel`.
- **Rationale:** Runtime validation, automatic serialization, clear contracts between modules.
- **Enforcement:** `mypy` + `pydantic` strict mode. No raw `dict` passing between workers and storage.
- **Required Models:** `ProfileSchema`, `PostSchema`, `RunSchema`, `AuditLogSchema`, `ConfigSchema`.

---

## Rule 3: Playwright for Browser Automation (No Selenium)

- **Mandate:** Browser automation MUST use Playwright. Selenium is strictly prohibited.
- **Rationale:** Playwright has better stealth, auto-waits, and handles modern JavaScript frameworks.
- **Enforcement:** Import check in CI. Any `selenium` import fails the build.
- **Required Pattern:** `sync_playwright()` context manager with explicit `browser.close()` in `finally`.

---

## Rule 4: httpx for HTTP Requests (No requests library)

- **Mandate:** All HTTP calls must use `httpx` (not `requests`).
- **Rationale:** Native async support, HTTP/2, better timeout handling, built-in retry middleware.
- **Enforcement:** Dependency check. `requests` is not in `requirements.txt`.
- **Required Pattern:** `httpx.AsyncClient` with `timeout=httpx.Timeout(30.0, connect=10.0)`.

---

## Rule 5: SQLite with WAL Mode as Primary Storage

- **Mandate:** SQLite is the ONLY primary database. WAL mode must be enabled.
- **Rationale:** Zero configuration, portable, ACID-compliant, sufficient for academic scale.
- **Enforcement:** Storage initialization runs `PRAGMA journal_mode = WAL` on every connection.
- **Forbidden:** PostgreSQL, MongoDB, or any external database for core storage.

---

## Rule 6: structlog for All Logging (No print statements)

- **Mandate:** Every log entry must use `structlog` with JSON rendering. `print()` is prohibited in production code.
- **Rationale:** Structured logs are queryable, machine-readable, and essential for audit trails.
- **Enforcement:** `flake8-print` plugin fails on any `print` in `src/`.
- **Required Pattern:** `logger = structlog.get_logger()` then `logger.info("event_name", key=value)`.

---

## Rule 7: Rate Limiting is Non-Optional

- **Mandate:** Every request to Instagram (API or browser) MUST pass through the rate limiter.
- **Rationale:** Compliance with ToS, avoiding IP bans, academic ethics.
- **Enforcement:** Workers cannot be instantiated without a `RateLimiter` instance. Unit tests verify enforcement.
- **Hard Limits:** Default 20 req/hour, max 50 req/day, 3 retries with exponential backoff.

---

## Rule 8: Zero Credential Storage in Code or Config Files

- **Mandate:** No API keys, tokens, or passwords in `.py`, `.yaml`, `.json`, or `.csv` files.
- **Rationale:** Security, git safety, compliance.
- **Enforcement:** `git-secrets` + `detect-secrets` pre-commit hooks. CI scans for patterns.
- **Required Pattern:** Environment variables only. `python-dotenv` loads from `.env` (gitignored).

---

## Rule 9: PII Must Be Stripped Before Storage

- **Mandate:** Raw usernames must be hashed. Emails, phone numbers, and locations must be removed or anonymized before any persistent storage.
- **Rationale:** GDPR/CCPA compliance, academic ethics, IRB requirements.
- **Enforcement:** Normalizer unit tests verify PII stripping. Integration tests check database contents.
- **Required Pattern:** `hashlib.sha256(username.encode()).hexdigest()` for identifiers. Regex for email/phone removal.

---

## Rule 10: Raw Data Auto-Deletion After 7 Days

- **Mandate:** Raw JSON responses in `data/raw/` must be automatically deleted after 7 days (configurable).
- **Rationale:** Data minimization principle, compliance with retention policies.
- **Enforcement:** Compliance module runs at end of every execution. Logs deletion with file count and bytes freed.
- **Required Pattern:** `compliance.enforce_retention()` called in `run.py` finally block.

---

## Rule 11: Every Module Must Have Unit Tests

- **Mandate:** Every `.py` file in `src/` must have a corresponding test file in `tests/` with >=80% coverage.
- **Rationale:** Reproducibility, confidence in refactoring, academic rigor.
- **Enforcement:** `pytest --cov=src --cov-fail-under=80` in CI.
- **Required Patterns:** Mock external calls (Playwright, httpx). Use `pytest-asyncio` for async tests.

---

## Rule 12: Async/Await for All I/O Operations

- **Mandate:** All network I/O (HTTP requests, browser operations) must use `async`/`await`.
- **Rationale:** Performance, non-blocking execution, proper resource utilization.
- **Enforcement:** `flake8-async` plugin. Blocking calls in async functions fail CI.
- **Exception:** SQLite operations may be sync (WAL mode handles concurrency).

---

## Rule 13: YAML for Configuration (No JSON Config)

- **Mandate:** All user-editable configuration must be in YAML format.
- **Rationale:** Human-readable, supports comments, nested structures, standard in DevOps.
- **Enforcement:** Config loader validates against Pydantic `ConfigSchema`. JSON config files rejected.
- **Required File:** `config/settings.yaml` with documented defaults.

---

## Rule 14: Circuit Breaker on 5 Consecutive Failures

- **Mandate:** After 5 consecutive target failures, the pipeline must pause for 1 hour (cooldown).
- **Rationale:** Prevent cascading failures, respect Instagram's infrastructure, avoid hard bans.
- **Enforcement:** `RateLimiter` tracks consecutive failures. State persisted to SQLite between runs.
- **Required Pattern:** Circuit breaker state: CLOSED -> OPEN (after 5 failures) -> HALF-OPEN (after 1h) -> CLOSED (on success).

---

## Rule 15: Git History Must Be Clean and Documented

- **Mandate:** Every commit must reference a task/issue. No "WIP", "fix", or "update" commit messages.
- **Rationale:** Academic reproducibility, team coordination, audit trail.
- **Enforcement:** `commitlint` pre-commit hook. Format: `type(scope): description [#issue]`.
- **Required Format:** `feat(rate_limiter): add circuit breaker logic [#12]` or `fix(parser): handle missing bio field [#15]`.

---

## Technology Mandates Summary

| Category | Required | Forbidden |
|----------|----------|-----------|
| Language | Python 3.10+ | Python <3.10 |
| Browser Automation | Playwright | Selenium, BeautifulSoup-only |
| HTTP Client | httpx | requests, urllib |
| Data Validation | Pydantic v2 | Raw dicts, dataclasses without validation |
| Storage | SQLite (WAL mode) | PostgreSQL, MongoDB, MySQL |
| Logging | structlog (JSON) | print, standard logging without structure |
| Scheduling | schedule library | Celery, Airflow, cron directly |
| Config Format | YAML | JSON config files |
| Testing | pytest + pytest-asyncio | unittest, no-test modules |
| Type Checking | mypy (strict) | Untyped code in src/ |

---

## Performance Constraints

| Constraint | Limit | Rationale |
|------------|-------|-----------|
| Memory per run | <512MB | Student laptop compatibility |
| Disk per 100 profiles | <10MB | Portable storage |
| Startup time | <5 seconds | Quick iteration |
| Test suite runtime | <60 seconds | Fast feedback loop |
| Single profile extraction | <30 seconds | Browser timeout safety |

---

## Safety & Quality Constraints

| Constraint | Enforcement |
|------------|-------------|
| No hardcoded URLs | All endpoints in config |
| No infinite loops | All loops have max iteration guards |
| No unhandled exceptions | Every worker has try/except/finally |
| No resource leaks | Context managers for browsers, files, DB connections |
| No blocking sleep in async | Use `asyncio.sleep` for async delays |
| No global mutable state | All state passed explicitly or stored in SQLite |

---

## Testing & Deployment Rules

| Rule | Requirement |
|------|-------------|
| Pre-commit hooks | black, isort, flake8, mypy, pytest (fast subset) |
| CI pipeline | Full test suite + coverage check + secret scan |
| Deployment | No deployment - local execution only |
| Environment | Virtualenv with pinned dependencies |
| Documentation | Every public method has Google-style docstring |
| README | Must include: install, configure, run, test, compliance notes |

---

## Violation Escalation

| Severity | Action |
|----------|--------|
| **CRITICAL** (Rules 1-5, 7-10) | Immediate rollback. Block merge. Require architectural review. |
| **HIGH** (Rules 6, 11-12, 14) | Block merge. Fix before approval. |
| **MEDIUM** (Rules 13, 15) | Warning. Fix in next commit. |

---

**End of AI_RULES**
