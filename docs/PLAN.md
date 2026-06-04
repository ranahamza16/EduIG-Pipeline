# PLAN.docx - Agent Execution Roadmap
## EduIG-Pipeline: Complete Build Plan for AI Agent (Antigravity)

**Version:** 2.0  
**Date:** 2026-05-31  
**Execution Mode:** AI Agent-Only (One Task At A Time)  
**Platform:** Google Antigravity  
**Agent Model:** Gemini 3.1 Pro / Claude Opus 4.6  
**Total Tasks:** 22  
**Estimated Agent Sessions:** 22-25  

---

## HOW TO USE THIS PLAN WITH ANTIGRAVITY

### Before Every Task
1. Read this PLAN.md to identify the CURRENT TASK
2. Read the relevant prompt from PROMPT_FOR_ANTIGRAVITY.md
3. Paste the prompt into Antigravity's **Plan Mode**
4. Review the agent's implementation plan
5. Approve → Switch to **Code Mode**
6. Wait for completion, review artifacts
7. Run tests locally to verify
8. Mark task as complete below
9. Move to NEXT TASK

### Rules for Working with the Agent
- **NEVER skip the Plan Mode review** — always check the plan before coding
- **ONE TASK PER SESSION** — do not ask agent to do multiple tasks
- **If agent fails a test** — paste the error, ask it to fix, do not proceed
- **If agent violates AI_RULES** — stop, reference the rule number, ask for correction
- **After every 4-5 tasks** — do a full test run to catch integration issues early

---

## TASK TRACKER

| # | Task | Phase | Status | Date Completed |
|---|------|-------|--------|----------------|
| 1 | Initialize Project Structure | Foundation | [ ] | |
| 2 | Virtual Environment & Dependencies | Foundation | [ ] | |
| 3 | Configuration System | Foundation | [ ] | |
| 4 | Structured Logger | Foundation | [ ] | |
| 5 | First Browser Worker | Foundation | [ ] | |
| 6 | Rate Limiter & Circuit Breaker | Core Pipeline | [ ] | |
| 7 | Pydantic Schemas | Core Pipeline | [ ] | |
| 8 | Router | Core Pipeline | [ ] | |
| 9 | Parser | Core Pipeline | [ ] | |
| 10 | Normalizer | Core Pipeline | [ ] | |
| 11 | SQLite Storage | Core Pipeline | [ ] | |
| 12 | Main Orchestrator (run.py) | Core Pipeline | [ ] | |
| 13 | PII Stripper & Compliance | Compliance | [ ] | |
| 14 | Error Handling & Resume | Compliance | [ ] | |
| 15 | Integration Tests | Compliance | [ ] | |
| 16 | Post Extraction | Advanced | [ ] | |
| 17 | Graph API Worker | Advanced | [ ] | |
| 18 | Jupyter Notebooks | Advanced | [ ] | |
| 19 | README & Documentation | Polish | [ ] | |
| 20 | Final Verification & Coverage | Polish | [ ] | |
| 21 | End-to-End Test Run | Polish | [ ] | |
| 22 | Compliance Report & Release | Polish | [ ] | |

---

## PHASE 1: FOUNDATION (Tasks 1-5)
**Goal:** Working repository, config, logger, and first successful scrape.
**Agent Sessions:** 5  
**Human Work:** Review plans, run tests, verify output  

---

### TASK 1: Initialize Project Structure
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** None  

**What Agent Must Do:**
1. Create full directory structure per ARCHITECTURE.md Section 5.1
2. Initialize Git repository with proper .gitignore
3. Create LICENSE file (MIT for academic use)
4. Create README.md skeleton with all sections
5. Create empty __init__.py files in all packages
6. Create .gitignore that excludes: venv/, data/, .env, __pycache__/, *.pyc, .pytest_cache/, .DS_Store
7. Create .env.example template
8. First commit with proper message format

**Deliverables:**
- Complete directory tree with all folders
- Git repo initialized with clean history
- README.md with TOC and section headers
- .gitignore tested (git status shows clean)

**Verification Command:**
```bash
git status  # Should be clean except untracked files
tree -L 3   # Should show full structure
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 1.1

---

### TASK 2: Virtual Environment & Dependencies
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 1  

**What Agent Must Do:**
1. Create requirements.txt with ALL dependencies and pinned versions
2. Create scripts/setup.sh that:
   - Checks Python version (>=3.10)
   - Creates virtual environment
   - Upgrades pip
   - Installs all requirements
   - Runs playwright install chromium
   - Runs a health check script
3. Create scripts/health_check.py that verifies all imports work
4. Create Makefile with common commands (install, test, lint, run)

**Dependencies List (pinned):**
```
playwright==1.41.0
httpx==0.26.0
pydantic==2.5.0
schedule==1.2.1
structlog==23.2.0
pandas==2.1.4
polars==0.20.0
pyyaml==6.0.1
python-dotenv==1.0.0
pytest==7.4.4
pytest-asyncio==0.23.0
pytest-cov==4.1.0
matplotlib==3.8.2
seaborn==0.13.0
jupyter==1.0.0
black==23.12.0
isort==5.13.0
mypy==1.7.0
flake8==7.0.0
```

**Deliverables:**
- requirements.txt with exact versions
- scripts/setup.sh (executable, tested)
- scripts/health_check.py (all imports succeed)
- Makefile with targets: install, test, lint, format, run

**Verification Command:**
```bash
make install
make health-check
python -c "import playwright, httpx, pydantic, structlog, pandas"
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 1.2

---

### TASK 3: Configuration System
**Priority:** P0  
**Estimated Time:** 1-2 agent sessions  
**Dependencies:** Task 2  

**What Agent Must Do:**
1. Create src/config_loader.py with:
   - Pydantic v2 ConfigSchema with nested models:
     - RateLimitConfig (requests_per_hour, base_delay, max_retries, backoff_factor, jitter_min, jitter_max, daily_cap)
     - PathsConfig (raw_data, processed, logs)
     - ComplianceConfig (max_profiles_per_run, delete_raw_after_days, require_consent, retention_enabled)
     - BrowserConfig (headless, viewport_width, viewport_height, timeout, user_agent)
     - APIConfig (base_url, timeout, max_connections)
     - LoggingConfig (level, format, rotation_days, retention_days)
   - load_config() function that reads YAML + env vars
   - Validation: requests_per_hour <= 50, delete_raw_after_days >= 1
   - Default values from PRD
2. Create config/settings.yaml with all defaults
3. Create config/.env.example with all env var names
4. Create config/targets.csv template with headers: username,url,consent_status,notes
5. Write tests: test_config_loader.py with >=80% coverage

**Deliverables:**
- src/config_loader.py (fully typed, validated)
- config/settings.yaml (documented, working)
- config/.env.example (complete template)
- config/targets.csv (template with sample row)
- tests/test_config_loader.py (all tests passing)

**Verification Command:**
```bash
python -c "from src.config_loader import load_config; c = load_config(); print(c.rate_limit.requests_per_hour)"
pytest tests/test_config_loader.py -v --cov=src.config_loader --cov-fail-under=80
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 1.3

---

### TASK 4: Structured Logger
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 3  

**What Agent Must Do:**
1. Create src/logger.py with:
   - configure_logging() function that sets up structlog
   - JSON renderer for production (configurable)
   - Console renderer with colors for development
   - Context binding: run_id, target, phase
   - Three log files in data/logs/:
     - app.log (all logs, daily rotation, 7-day retention)
     - error.log (ERROR+, daily rotation, 30-day retention)
     - audit.log (compliance events, NEVER auto-delete)
   - Log format: ISO timestamp, event name, key-value pairs
2. Write tests: test_logger.py
3. Ensure no print() statements anywhere in src/

**Deliverables:**
- src/logger.py (importable, configurable)
- data/logs/ directory auto-created
- Test that verifies JSON output format
- Test that verifies log file rotation

**Verification Command:**
```bash
python -c "from src.logger import get_logger; logger = get_logger(); logger.info('test_event', key='value')"
pytest tests/test_logger.py -v
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 1.4

---

### TASK 5: First Browser Worker
**Priority:** P0  
**Estimated Time:** 1-2 agent sessions  
**Dependencies:** Task 4  

**What Agent Must Do:**
1. Create src/browser_worker.py with:
   - BrowserWorker class
   - __init__(self, config: ConfigSchema, logger)
   - extract_public_profile(self, username: str) -> ProfileSchema
   - Uses Playwright sync API with:
     - headless=True (configurable)
     - viewport 1280x800
     - Accept-Language: en-US,en;q=0.9 header
     - 3-second wait after page load
     - page.evaluate() for JSON extraction (PRIMARY method)
     - CSS selector fallback if JSON fails
     - Proper cleanup: browser.close() in finally block
   - Returns ProfileSchema with all fields
   - Logs every step to audit log
2. Create src/schemas.py with ProfileSchema (if not done in Task 7, do it here)
3. Write tests with mocked Playwright
4. Document known limitations (Instagram DOM changes)

**Deliverables:**
- src/browser_worker.py (working extraction)
- src/schemas.py (ProfileSchema at minimum)
- tests/test_browser_worker.py (mocked tests)
- Successful extraction of 1 test profile

**Verification Command:**
```bash
python -c "from src.browser_worker import BrowserWorker; from src.config_loader import load_config; bw = BrowserWorker(load_config()); print('BrowserWorker ready')"
pytest tests/test_browser_worker.py -v
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 1.5

**CHECKPOINT:** After Task 5, verify you can extract a real Instagram profile. If not, debug before proceeding.

---

## PHASE 2: CORE PIPELINE (Tasks 6-12)
**Goal:** All modules connected, data flows end-to-end, tests passing.
**Agent Sessions:** 7  
**Human Work:** Review integration, run full pipeline on 5 targets  

---

### TASK 6: Rate Limiter & Circuit Breaker
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 5  

**What Agent Must Do:**
1. Create src/rate_limiter.py with:
   - LeakyBucket class:
     - __init__(self, requests_per_hour: int)
     - wait(self) -> None: sleeps min_interval * jitter
     - get_state(self) -> dict: returns current bucket state
   - exponential_backoff(attempt: int, base: float, max_retries: int) -> float
   - CircuitBreaker class:
     - States: CLOSED, OPEN, HALF_OPEN
     - failure_threshold: int (default 5)
     - cooldown_seconds: int (default 3600)
     - record_success(), record_failure()
     - can_execute() -> bool
     - get_state() -> str
   - DailyCap class: tracks requests per day, hard stops at limit
   - All timing uses asyncio (async/await)
2. Write comprehensive tests with mocked time
3. Test circuit breaker state transitions

**Deliverables:**
- src/rate_limiter.py (all classes)
- tests/test_rate_limiter.py (state machine tests, timing tests)
- >=80% coverage

**Verification Command:**
```bash
pytest tests/test_rate_limiter.py -v --cov=src.rate_limiter --cov-fail-under=80
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 2.1

---

### TASK 7: Pydantic Schemas
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 6  

**What Agent Must Do:**
1. Create src/schemas.py with Pydantic v2 models:
   - ProfileSchema:
     - profile_id: str (hashed)
     - username_hash: str (SHA-256)
     - bio: str | None
     - followers: int | None
     - following: int | None
     - posts_count: int | None
     - extracted_at: datetime
     - source: Literal["api", "browser"]
     - Custom validators: strip whitespace, truncate bio to 500 chars
   - PostSchema:
     - post_id: str
     - profile_id: str
     - caption: str | None
     - likes: int | None
     - comments: int | None
     - hashtags: list[str]
     - posted_at: datetime | None
     - engagement_rate: float | None
   - RunSchema:
     - run_id: str
     - started_at: datetime
     - completed_at: datetime | None
     - targets_count: int
     - success_count: int
     - failure_count: int
   - AuditLogSchema:
     - timestamp: datetime
     - run_id: str
     - target: str
     - action: str
     - status: Literal["success", "failure", "skipped"]
     - bytes_collected: int
     - compliance_note: str
     - error_message: str | None
   - TargetSchema:
     - username: str
     - url: str
     - consent_status: Literal["granted", "denied", "pending", "public_only"]
     - notes: str | None
2. All models must have:
   - model_config = ConfigDict(strict=False)
   - to_json() method
   - from_json() classmethod
3. Write tests for all validators

**Deliverables:**
- src/schemas.py (all 5 models)
- tests/test_schemas.py (validation tests, serialization tests)

**Verification Command:**
```bash
pytest tests/test_schemas.py -v --cov=src.schemas --cov-fail-under=80
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 2.3

---

### TASK 8: Router
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 7  

**What Agent Must Do:**
1. Create src/router.py with:
   - Router class:
     - __init__(self, config, api_worker, browser_worker, logger)
     - route(self, target: TargetSchema) -> Worker
     - Decision logic:
       - If has_valid_oauth() AND target.consent_status == "granted": return api_worker
       - Elif target is public: return browser_worker
       - Else: log skip, return None
     - has_valid_oauth() -> bool: checks env var, validates token format
   - Log every routing decision to audit log
2. Write tests with mocked workers

**Deliverables:**
- src/router.py (routing logic)
- tests/test_router.py (all decision paths tested)

**Verification Command:**
```bash
pytest tests/test_router.py -v --cov=src.router --cov-fail-under=80
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 2.2

---

### TASK 9: Parser
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 8  

**What Agent Must Do:**
1. Create src/parser.py with:
   - Parser class:
     - parse_api_response(self, raw_data: dict) -> dict:
       - Extracts fields from Graph API JSON
       - Handles missing fields (None instead of KeyError)
       - Maps API field names to internal names
     - parse_browser_response(self, raw_data: dict) -> dict:
       - Extracts from Playwright page.evaluate() output
       - Handles DOM structure variations
     - parse_post_data(self, raw_posts: list) -> list[PostSchema]:
       - Extracts 10 most recent posts
       - Parses hashtags from caption via regex
       - Converts engagement strings to ints
     - _parse_count(self, value: str | int) -> int | None:
       - Handles "1.2k", "3.4M", "5,678" formats
     - _parse_timestamp(self, value: str) -> datetime | None:
       - Handles Instagram timestamp formats
2. Write tests with sample JSON data

**Deliverables:**
- src/parser.py (all parsing methods)
- tests/test_parser.py (sample data tests)
- Sample JSON fixtures in tests/fixtures/

**Verification Command:**
```bash
pytest tests/test_parser.py -v --cov=src.parser --cov-fail-under=80
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 2.4

---

### TASK 10: Normalizer
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 9  

**What Agent Must Do:**
1. Create src/normalizer.py with:
   - Normalizer class:
     - normalize_profile(self, raw_data: dict, source: str) -> ProfileSchema:
       - Schema mapping
       - PII stripping:
         - SHA-256 hash username: hashlib.sha256(username.encode()).hexdigest()
         - Remove emails: regex r'[\w.-]+@[\w.-]+\.\w+'
         - Remove phones: regex r'\+?\d[\d\s-]{7,}\d'
         - Strip URLs from bio
       - Type coercion
       - Deduplication: check if profile_id exists in DB
     - normalize_posts(self, raw_posts: list, profile_id: str) -> list[PostSchema]:
       - Calculate engagement_rate
       - Extract hashtags
       - Validate all fields
     - _strip_pii(self, text: str) -> str: removes all PII patterns
     - _hash_username(self, username: str) -> str: deterministic hash
   - All methods return Pydantic-validated objects
2. Write tests with PII-containing sample data

**Deliverables:**
- src/normalizer.py (normalization + PII stripping)
- tests/test_normalizer.py (PII removal verification)
- tests/fixtures/pii_samples.json (test data)

**Verification Command:**
```bash
pytest tests/test_normalizer.py -v --cov=src.normalizer --cov-fail-under=80
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 2.5

---

### TASK 11: SQLite Storage
**Priority:** P0  
**Estimated Time:** 1-2 agent sessions  
**Dependencies:** Task 10  

**What Agent Must Do:**
1. Create src/storage.py with:
   - StorageManager class:
     - __init__(self, db_path: str, logger):
       - Creates connection with WAL mode
       - PRAGMA journal_mode = WAL
       - PRAGMA foreign_keys = ON
       - PRAGMA synchronous = NORMAL
     - _create_tables(self): creates all tables
       - profiles (profile_id PRIMARY KEY, username_hash, bio, followers, following, posts_count, extracted_at, source)
       - posts (post_id PRIMARY KEY, profile_id FOREIGN KEY, caption, likes, comments, hashtags, posted_at, engagement_rate)
       - runs (run_id PRIMARY KEY, started_at, completed_at, targets_count, success_count, failure_count)
       - audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp, run_id, target, action, status, bytes_collected, compliance_note, error_message)
     - save_profile(self, profile: ProfileSchema) -> bool
     - save_posts(self, posts: list[PostSchema]) -> int
     - save_run(self, run: RunSchema) -> str
     - save_audit_log(self, entry: AuditLogSchema) -> None
     - get_profile(self, profile_id: str) -> ProfileSchema | None
     - export_to_csv(self, run_id: str, output_dir: str) -> list[str]
     - export_to_json(self, raw_data: dict, filepath: str) -> None
     - check_duplicate(self, profile_id: str) -> bool
     - close(self): closes connection
   - Context manager support (with statement)
   - Atomic transactions
2. Write integration tests with in-memory SQLite
3. Test CSV export format

**Deliverables:**
- src/storage.py (full CRUD + export)
- tests/test_storage.py (all operations tested)
- Verified CSV export with headers

**Verification Command:**
```bash
pytest tests/test_storage.py -v --cov=src.storage --cov-fail-under=80
python -c "from src.storage import StorageManager; s = StorageManager(':memory:'); print('Storage ready')"
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 2.6

---

### TASK 12: Main Orchestrator (run.py)
**Priority:** P0  
**Estimated Time:** 1-2 agent sessions  
**Dependencies:** Task 11  

**What Agent Must Do:**
1. Create run.py with:
   - CLI argument parsing (argparse):
     - --config (path to settings.yaml)
     - --dry-run (validate without scraping)
     - --resume run_id (resume interrupted run)
     - --export-csv (export existing data)
     - --test-profile username (test single extraction)
   - async main() function:
     - Load config
     - Initialize logger
     - Create storage manager
     - Read targets.csv
     - Create run record in DB
     - For each target:
       - RateLimiter.wait()
       - Router.route(target) -> worker
       - Worker.extract() -> raw_data
       - Parser.parse() -> parsed_data
       - Normalizer.normalize() -> clean_data
       - Storage.save() -> persisted
       - Audit log entry
     - Handle KeyboardInterrupt gracefully
     - Save progress on unexpected exit
     - Run compliance cleanup
     - Generate summary report
   - SIGINT/SIGTERM handlers
   - Resume logic: reads last successful target from DB
2. Write integration tests with mocked workers
3. Test dry-run mode
4. Test resume functionality

**Deliverables:**
- run.py (complete orchestrator)
- tests/test_run.py (integration tests)
- Successful dry-run: python run.py --dry-run

**Verification Command:**
```bash
python run.py --dry-run
pytest tests/test_run.py -v
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 2.7

**CHECKPOINT:** After Task 12, run full pipeline on 5 test targets. Verify data in all three formats (SQLite, JSON, CSV). Debug before proceeding.

---

## PHASE 3: COMPLIANCE & ROBUSTNESS (Tasks 13-15)
**Goal:** Production-grade compliance, error handling, full test coverage.
**Agent Sessions:** 3  
**Human Work:** Verify compliance rules, inspect audit logs  

---

### TASK 13: PII Stripper & Compliance Engine
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 12  

**What Agent Must Do:**
1. Create src/compliance.py with:
   - PIIStripper class:
     - strip_bio(self, text: str) -> str: removes emails, phones, URLs
     - hash_username(self, username: str) -> str: SHA-256
     - anonymize_location(self, text: str) -> str: removes location mentions
   - ConsentTracker class:
     - check_consent(self, target: TargetSchema) -> bool
     - log_consent_violation(self, target: TargetSchema) -> None
   - RetentionEnforcer class:
     - enforce_retention(self, raw_dir: str, days: int) -> dict:
       - Finds files older than N days
       - Deletes them securely
       - Returns deletion log
     - schedule_cleanup(self): sets up scheduled cleanup
   - ExportController class:
     - verify_export(self, csv_path: str) -> bool: checks for PII leaks
     - sanitize_csv(self, input_path: str, output_path: str) -> None
   - AuditGenerator class:
     - generate_report(self, run_id: str) -> str: produces markdown compliance report
     - Includes: targets processed, PII checks passed, retention status, consent status
2. Write tests with PII-containing data
3. Test retention enforcement with temp files

**Deliverables:**
- src/compliance.py (all compliance classes)
- tests/test_compliance.py (PII removal, retention, consent)
- Sample compliance report generated

**Verification Command:**
```bash
pytest tests/test_compliance.py -v --cov=src.compliance --cov-fail-under=80
python -c "from src.compliance import AuditGenerator; print('Compliance ready')"
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 3.1

---

### TASK 14: Error Handling & Resilience
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 13  

**What Agent Must Do:**
1. Enhance all workers with:
   - Try/except/finally around ALL external calls
   - Graceful degradation: save partial data on failure
   - Resume capability:
     - Save run state to SQLite after each target
     - Track last successful target index
     - On resume, skip completed targets
   - Dry-run mode: validate targets without network calls
   - Detailed error context in logs
2. Update run.py with:
   - Keyboard interrupt handling (save state, close browser)
   - Unexpected exit handling (atexit hooks)
   - Resume from last successful target
3. Write resilience tests:
   - Simulate network failure mid-run
   - Verify state is saved
   - Verify resume works

**Deliverables:**
- Enhanced error handling in all workers
- Resume logic in run.py
- tests/test_resilience.py (failure simulation)

**Verification Command:**
```bash
pytest tests/test_resilience.py -v
python run.py --resume run_001  # Test actual resume
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 3.2

---

### TASK 15: Integration Tests & Coverage
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 14  

**What Agent Must Do:**
1. Create tests/integration/test_pipeline.py with:
   - Mock Playwright and httpx
   - Test full pipeline with 3 fake targets
   - Verify rate limiting is enforced (count requests)
   - Verify data flows through all modules correctly
   - Verify compliance rules are applied (check DB for hashed usernames)
   - Verify audit logs are written (count entries)
   - Verify raw JSON is written
   - Verify CSV export works
2. Create tests/integration/test_compliance.py with:
   - Test PII stripping end-to-end
   - Test retention enforcement
   - Test consent checking
3. Achieve >=80% total coverage across all modules
4. Create pytest.ini with markers: unit, integration, slow

**Deliverables:**
- tests/integration/ folder with 2 test files
- pytest.ini configuration
- Coverage report showing >=80%

**Verification Command:**
```bash
pytest --cov=src --cov-fail-under=80 --cov-report=html
# Open htmlcov/index.html to verify
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 3.3

**CHECKPOINT:** After Task 15, run full test suite. If coverage <80%, ask agent to add tests. If any test fails, fix before proceeding.

---

## PHASE 4: ADVANCED FEATURES (Tasks 16-18)
**Goal:** Post extraction, engagement metrics, API worker, analysis notebooks.
**Agent Sessions:** 3  
**Human Work:** Review notebook outputs, verify engagement calculations  

---

### TASK 16: Post Extraction & Engagement Metrics
**Priority:** P1  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 15  

**What Agent Must Do:**
1. Extend src/browser_worker.py with:
   - extract_posts(self, username: str, limit: int = 10) -> list[PostSchema]:
     - Extracts N most recent posts from profile page
     - Handles pagination truncation (document limitation)
     - Extracts: caption, likes, comments, timestamp, hashtags
   - extract_hashtags(self, caption: str) -> list[str]: regex #\w+
2. Update src/schemas.py PostSchema if needed
3. Update src/parser.py to handle post data
4. Update src/normalizer.py to calculate engagement_rate
5. Update src/storage.py to save posts with foreign key
6. Write tests with sample post data

**Deliverables:**
- Enhanced browser_worker.py with post extraction
- Engagement rate calculation verified
- tests/test_posts.py (post extraction tests)

**Verification Command:**
```bash
pytest tests/test_posts.py -v
# Manual test: extract 1 profile with posts, verify engagement_rate
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 4.1

---

### TASK 17: Graph API Worker
**Priority:** P1  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 16  

**What Agent Must Do:**
1. Create src/api_worker.py with:
   - APIWorker class:
     - __init__(self, config, logger):
       - Sets up httpx.AsyncClient with timeout
       - Reads OAuth token from env var
     - _get_headers(self) -> dict: Bearer token header
     - _refresh_token(self) -> str: token refresh logic (if applicable)
     - get_user_profile(self, user_id: str) -> dict:
       - Calls /{user-id} endpoint
       - Handles rate limit headers
     - get_user_media(self, user_id: str, limit: int = 10) -> list[dict]:
       - Calls /{user-id}/media
       - Paginates if needed
     - get_media_insights(self, media_id: str) -> dict:
       - Calls /{media-id}/insights
     - All methods handle: token expiry, permission errors, quota exceeded
   - Only activates when OAuth token is present AND consent is granted
2. Write tests with mocked httpx
3. Document: this is OPTIONAL, pipeline works without it

**Deliverables:**
- src/api_worker.py (complete API client)
- tests/test_api_worker.py (mocked API tests)
- Documentation: optional feature

**Verification Command:**
```bash
pytest tests/test_api_worker.py -v --cov=src.api_worker --cov-fail-under=80
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 4.2

---

### TASK 18: Jupyter Analysis Notebooks
**Priority:** P1  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 17  

**What Agent Must Do:**
1. Create notebooks/01_exploratory_analysis.ipynb with:
   - Load data from SQLite into pandas
   - Basic statistics: profile count, follower distribution, post count
   - Distribution plots (matplotlib/seaborn)
   - Missing data analysis
   - Markdown explanations for each section
2. Create notebooks/02_engagement_metrics.ipynb with:
   - Engagement rate distribution
   - Correlation analysis (followers vs engagement)
   - Top performing posts
   - Hashtag frequency analysis
   - Visualizations with clear labels
3. Create notebooks/03_compliance_report.ipynb with:
   - Verify PII stripping: check for raw usernames, emails, phones
   - Audit log analysis: success rate, failure reasons
   - Retention compliance: verify raw data deletion
   - Summary statistics for IRB report
4. All notebooks must:
   - Have clear markdown explanations
   - Be runnable top-to-bottom
   - Use relative paths (../data/)
   - Include cell outputs (committed as examples)

**Deliverables:**
- 3 complete Jupyter notebooks
- Sample outputs in committed versions
- README section on notebooks

**Verification Command:**
```bash
jupyter nbconvert --execute notebooks/01_exploratory_analysis.ipynb --to html
# Check that HTML output is generated without errors
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 4.3

**CHECKPOINT:** After Task 18, run all notebooks with real data. Verify outputs make sense. Fix any visualization issues.

---

## PHASE 5: POLISH & RELEASE (Tasks 19-22)
**Goal:** Professional documentation, final verification, release.
**Agent Sessions:** 4  
**Human Work:** Final review, approve release  

---

### TASK 19: README & Documentation
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 18  

**What Agent Must Do:**
1. Complete README.md with:
   - Title + badges (Python version, license, tests)
   - Overview (2-3 sentences)
   - Features list (P0, P1, P2)
   - Architecture diagram (ASCII art or mermaid)
   - Installation: step-by-step with commands
   - Configuration: explain settings.yaml and .env
   - Usage: all run.py commands with examples
   - Testing: how to run tests
   - Compliance: ethics, IRB, data minimization
   - Citation: how to cite this tool
   - Contributing: link to CONTRIBUTING.md
   - License: MIT
   - Acknowledgments
2. Create CONTRIBUTING.md with:
   - Branch strategy (dev-a/feature-name)
   - Commit format (feat(scope): description [#issue])
   - PR process (template)
   - Code review checklist
   - Development setup
3. Add architecture diagrams to README
4. Ensure all public methods have Google-style docstrings

**Deliverables:**
- README.md (complete, professional)
- CONTRIBUTING.md (team coordination)
- All docstrings complete

**Verification Command:**
```bash
# Read README and verify all sections present
# Check docstrings: pydoc src.browser_worker
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 5.1

---

### TASK 20: Final Verification & Quality Checks
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 19  

**What Agent Must Do:**
1. Run complete verification:
   - pytest --cov=src --cov-fail-under=80
   - mypy src/ --strict
   - black src/ --check
   - isort src/ --check-only
   - flake8 src/ --max-line-length=100
   - Check for print statements: grep -r "print(" src/ (should be empty)
   - Check for secrets: git-secrets --scan
2. Fix ALL issues found
3. Ensure no TODO or FIXME comments in src/
4. Ensure all exception handlers log errors
5. Create .pre-commit-config.yaml with:
   - black, isort, flake8, mypy, pytest (fast)
   - git-secrets
6. Create GitHub Actions workflow (optional): .github/workflows/ci.yml

**Deliverables:**
- All quality checks passing
- .pre-commit-config.yaml
- CI workflow (optional)
- Clean code with no warnings

**Verification Command:**
```bash
make test      # Should pass
make lint      # Should pass
make typecheck # Should pass
make format    # Should apply formatting
```

**Prompt to Use:** PROMPT_FOR_ANTIGRAVITY.md Section 3, Task 5.2

---

### TASK 21: End-to-End Test Run
**Priority:** P0  
**Estimated Time:** 1 agent session (mostly human monitoring)  
**Dependencies:** Task 20  

**What Agent Must Do:**
1. Create a test targets.csv with 10 public Instagram profiles
2. Run: python run.py --config config/settings.yaml
3. Monitor for:
   - Rate limiting working (check delays between requests)
   - Data in SQLite (check profiles table)
   - Raw JSON in data/raw/ (check files created)
   - CSV in data/processed/ (check export)
   - Audit logs in data/logs/audit.log (check entries)
   - No errors in data/logs/error.log
4. Verify data quality:
   - Usernames are hashed (not plaintext)
   - No emails/phones in bios
   - Engagement rates calculated
   - Post data present (if Task 16 done)
5. Generate test run report
6. Document any issues found

**Deliverables:**
- Successful test run on 10 profiles
- Test run report (markdown)
- Data quality verification checklist

**Verification Command:**
```bash
python run.py
sqlite3 data/eduig.db "SELECT COUNT(*) FROM profiles;"
sqlite3 data/eduig.db "SELECT COUNT(*) FROM posts;"
cat data/logs/audit.log | wc -l
ls data/raw/ | wc -l
ls data/processed/ | wc -l
```

**Human Action Required:**
- Monitor the run (takes ~30-60 minutes for 10 profiles at 20/hour)
- Check Instagram doesn't block IP
- Verify output quality

---

### TASK 22: Compliance Report & Release
**Priority:** P0  
**Estimated Time:** 1 agent session  
**Dependencies:** Task 21  

**What Agent Must Do:**
1. Generate compliance_report.md with:
   - Project overview
   - Data collection period
   - Number of targets processed
   - PII handling confirmation (hashed usernames, stripped bios)
   - Retention policy status (raw data deleted after 7 days)
   - Consent tracking summary
   - Audit log summary
   - Rate limiting compliance
   - ToS acknowledgment
   - Data deletion confirmation
   - IRB reference (if applicable)
2. Create CHANGELOG.md with all tasks completed
3. Tag release: git tag -a v1.0 -m "EduIG-Pipeline v1.0 - MVP Release"
4. Create final summary document: PROJECT_SUMMARY.md
   - What was built
   - Key features
   - Technology stack
   - How to use
   - Known limitations
   - Future improvements
5. Clean up:
   - Delete any test data from repo
   - Ensure .env is gitignored
   - Ensure data/ is gitignored
   - Final git status check

**Deliverables:**
- compliance_report.md
- CHANGELOG.md
- PROJECT_SUMMARY.md
- Git tag v1.0
- Clean repository

**Verification Command:**
```bash
git status        # Should be clean
git tag -l        # Should show v1.0
git log --oneline # Should show all tasks
```

---

## QUALITY GATES BETWEEN PHASES

### Gate 1: Foundation -> Core Pipeline
**Requirements:**
- [ ] Can load config and print it
- [ ] Can extract 1 profile successfully
- [ ] Logger writes JSON to file
- [ ] All 5 tasks have tests passing

### Gate 2: Core Pipeline -> Compliance
**Requirements:**
- [ ] Full pipeline runs on 5 targets end-to-end
- [ ] Data in SQLite, JSON, and CSV
- [ ] Rate limiting enforced (check timestamps)
- [ ] All 7 tasks have tests passing
- [ ] Coverage >=80%

### Gate 3: Compliance -> Advanced
**Requirements:**
- [ ] Usernames hashed in database
- [ ] No PII in stored data
- [ ] Audit logs complete
- [ ] Raw data retention works
- [ ] Integration tests pass

### Gate 4: Advanced -> Polish
**Requirements:**
- [ ] Post extraction works
- [ ] Engagement rates calculated
- [ ] Notebooks run without errors
- [ ] API worker functional (optional)

### Gate 5: Polish -> Release
**Requirements:**
- [ ] All quality checks pass (black, isort, mypy, flake8, pytest)
- [ ] README is complete and clear
- [ ] Test run on 10 profiles successful
- [ ] Compliance report generated
- [ ] Git tag v1.0 created

---

## AGENT SESSION TIPS

### Before Each Session
1. Read the task description in this PLAN
2. Read the matching prompt in PROMPT_FOR_ANTIGRAVITY.md
3. Check off any previously completed tasks
4. Ensure your local environment is clean (git status)

### During Each Session
1. Start Antigravity in Plan Mode
2. Paste the prompt + any context from previous tasks
3. Review the plan carefully - add requirements if missing
4. Approve the plan
5. Let agent code in Code Mode
6. Review artifacts as they appear
7. Ask for corrections if something looks wrong

### After Each Session
1. Run tests locally: pytest tests/test_<module>.py -v
2. Check coverage: pytest --cov=src.<module> --cov-fail-under=80
3. Run type check: mypy src/<module>.py --strict
4. Check formatting: black --check src/<module>.py
5. Git commit with proper format: feat(module): description [#task-num]
6. Mark task complete in tracker above
7. Take a screenshot of test results for records

### If Agent Gets Stuck
1. Cancel current session
2. Re-read the task - maybe requirements unclear
3. Simplify: ask agent to do a smaller part first
4. Switch model: try Claude Opus 4.6 instead of Gemini 3.1 Pro
5. Check AI_RULES: maybe agent violated a rule and got confused
6. Search for similar issues in the skill files

### If Tests Fail After Agent Says "Done"
1. Paste the exact error into new agent session
2. Ask: "Fix this test failure. Do not change unrelated code."
3. Verify fix doesn't break other tests
4. Re-run full test suite before proceeding

---

## EXPECTED TOTAL TIME

| Phase | Tasks | Agent Sessions | Human Time | Cumulative |
|-------|-------|----------------|------------|------------|
| Foundation | 5 | 5-7 | 2-3 hours | Week 1 |
| Core Pipeline | 7 | 7-9 | 3-4 hours | Week 2 |
| Compliance | 3 | 3-4 | 1-2 hours | Week 3 |
| Advanced | 3 | 3-4 | 2-3 hours | Week 4 |
| Polish | 4 | 4-5 | 2-3 hours | Week 5 |
| **Total** | **22** | **22-29** | **10-15 hours** | **5 weeks** |

**Note:** Human time is mostly review, testing, and approval. Agent does the coding.

---

**End of PLAN**
