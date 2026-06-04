# EduIG-Pipeline Code Style Rules
# File: .agents/rules/eduig-code-style.md
# Enforcement: Automated linting + mypy + manual review

## Language & Standards
- Python 3.10+ ONLY. Use `str | None` union syntax, never `Optional`.
- All data models MUST be Pydantic v2 BaseModel classes.
- Every public function MUST have Google-style docstrings.
- Type hints required on ALL function signatures.
- No `print()` statements — use structlog JSON logging only.

## Architecture Rules
- Browser automation: Playwright ONLY (no Selenium).
- HTTP requests: httpx ONLY (no requests library).
- Storage: SQLite with WAL mode ONLY (no PostgreSQL/MongoDB).
- Config: YAML ONLY (no JSON config files).
- All network I/O operations MUST use async/await.
- SQLite operations may be synchronous (WAL handles concurrency).

## Quality Rules
- Every .py file in src/ MUST have a test file in tests/.
- Minimum 80% test coverage (pytest --cov).
- mypy strict mode must pass on all src/ files.
- black + isort formatting required before every commit.
- No hardcoded URLs, credentials, or API keys in code.
- No magic numbers — use named constants from config.
- No bare except clauses — always catch specific exceptions.
- All loops must have max iteration guards (no infinite loops).
- All external calls must have try/except/finally.

## Compliance Rules
- Raw usernames MUST be SHA-256 hashed before storage.
- Emails/phones in bios MUST be stripped via regex before storage.
- Raw JSON data MUST auto-delete after 7 days (configurable).
- Every extraction MUST log to audit trail with compliance_note.
- Circuit breaker opens after 5 consecutive failures.
- No credential storage in .py, .yaml, .json, or .csv files.

## Naming Conventions
- Classes: PascalCase (e.g., `BrowserWorker`, `RateLimiter`)
- Functions/methods: snake_case (e.g., `extract_profile`, `wait_for_rate_limit`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- Private methods: leading underscore (e.g., `_strip_pii`, `_hash_username`)
- Files: snake_case (e.g., `browser_worker.py`, `rate_limiter.py`)
