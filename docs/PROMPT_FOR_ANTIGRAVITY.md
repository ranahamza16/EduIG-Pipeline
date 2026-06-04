# PROMPT_FOR_ANTIGRAVITY.docx - Master Instruction Set for Antigravity Agent
## EduIG-Pipeline: How to Build This Project Using Antigravity's Agent-First IDE

**Version:** 1.0  
**Date:** 2026-05-31  
**Target Platform:** Google Antigravity (Agent-First IDE)  
**Agent Mode:** Plan Mode -> Review -> Code Mode (One Task At A Time)  
**Model Recommendation:** Gemini 3.1 Pro (complex reasoning) or Claude Opus 4.6 (detailed implementation)  

---

## SECTION 1: INITIAL SETUP INSTRUCTIONS FOR ANTIGRAVITY

### Step 1: Create Workspace Rules (BEFORE any coding)

Create the following rule files in your Antigravity workspace at `.agents/rules/`:

**File: `.agents/rules/eduig-code-style.md`**
```
# EduIG-Pipeline Code Style Rules

## Language & Standards
- Python 3.10+ ONLY. Use `str | None` union syntax, never `Optional`.
- All data models MUST be Pydantic v2 BaseModel classes.
- Every public function MUST have Google-style docstrings.
- Type hints required on ALL function signatures.
- No `print()` statements - use structlog JSON logging only.

## Architecture Rules
- Browser automation: Playwright ONLY (no Selenium).
- HTTP requests: httpx ONLY (no requests library).
- Storage: SQLite with WAL mode ONLY (no PostgreSQL/MongoDB).
- Config: YAML ONLY (no JSON config files).
- All I/O operations MUST use async/await.

## Quality Rules
- Every .py file in src/ MUST have a test file in tests/.
- Minimum 80% test coverage (pytest --cov).
- mypy strict mode must pass.
- black + isort formatting required.
- No hardcoded URLs, credentials, or API keys in code.
- No magic numbers - use named constants from config.

## Compliance Rules
- Raw usernames MUST be SHA-256 hashed before storage.
- Emails/phones in bios MUST be stripped via regex before storage.
- Raw JSON data MUST auto-delete after 7 days.
- Every extraction MUST log to audit trail.
- Circuit breaker opens after 5 consecutive failures.
```

**File: `.agents/rules/eduig-git-rules.md`**
```
# EduIG-Pipeline Git Commit Rules

## Commit Message Format
<type>(<scope>): <description> [#<issue-number>]

## Types
- feat: new feature
- fix: bug fix
- docs: documentation only
- test: adding or updating tests
- refactor: code change that neither fixes bug nor adds feature
- perf: performance improvement
- chore: build process or auxiliary tool changes

## Examples
- feat(rate_limiter): add circuit breaker logic [#12]
- fix(parser): handle missing bio field [#15]
- test(storage): add WAL mode concurrency tests [#8]
- docs(readme): add installation instructions [#3]
```

### Step 2: Create Workspace Skills

Create the following skill folders in `.agents/skills/` (copy from the provided skill files):

| Skill Folder | Source Skill File | Purpose |
|--------------|-------------------|---------|
| `web-scraper` | `/app/.agents/skills/web-scraper/SKILL.md` | Multi-strategy web scraping guidance |
| `bash-scripting` | `/app/.agents/skills/bash-scripting/SKILL.md` | Production-ready shell scripts |
| `api-patterns` | `/app/.agents/skills/api-patterns/SKILL.md` | API design principles |
| `workflow-automation` | `/app/.agents/skills/workflow-automation/SKILL.md` | Agent workflow orchestration |

### Step 3: Create Workflow Files

**File: `.agents/workflows/eduig-build-phase.md`**
```
# Title: EduIG Build Phase Workflow
# Description: Execute one phase of the EduIG-Pipeline implementation

Step 1: Read the PLAN.md document to identify the current phase and tasks.
Step 2: Read the ARCHITECTURE.md document to understand module design.
Step 3: Read the AI_RULES.md document to verify compliance constraints.
Step 4: Create a detailed implementation plan for THIS TASK ONLY.
Step 5: Write the code following all rules and skills.
Step 6: Write unit tests for the new code (minimum 80% coverage).
Step 7: Run tests and fix any failures.
Step 8: Run mypy type checking and fix any errors.
Step 9: Run black + isort formatting.
Step 10: Update documentation (README or inline docs).
Step 11: Generate a walkthrough artifact summarizing what was built.
```

**File: `.agents/workflows/eduig-test-and-verify.md`**
```
# Title: EduIG Test & Verify Workflow
# Description: Run full test suite and verify compliance

Step 1: Run pytest with coverage: `pytest --cov=src --cov-fail-under=80`
Step 2: Run mypy strict: `mypy src/ --strict`
Step 3: Run formatting check: `black --check src/ && isort --check-only src/`
Step 4: Verify no secrets in code: `git-secrets --scan`
Step 5: Check for print statements: `flake8-print src/`
Step 6: Run integration test on 5 test profiles.
Step 7: Verify audit log entries exist.
Step 8: Verify raw data retention policy.
Step 9: Generate compliance report.
```

---

## SECTION 2: MASTER PROMPT FOR ANTIGRAVITY

### Initial Project Setup Prompt

```
I am building EduIG-Pipeline, an educational Instagram data acquisition system 
for academic research. This is a Python 3.10+ project using Playwright, Pydantic v2, 
httpx, SQLite, and structlog.

PHASE: Foundation (Week 1)
CURRENT TASK: Initialize the project repository and create the core configuration system.

CONTEXT:
- This is a 2-student academic project. Code must be clean, well-documented, and reproducible.
- The project has strict compliance requirements: PII stripping, rate limiting, audit logging.
- All code must follow the workspace rules in .agents/rules/eduig-code-style.md.

WHAT I NEED YOU TO DO:
1. Create the project directory structure as specified in ARCHITECTURE.md Section 5.1.
2. Initialize a Git repository with proper .gitignore (Python, secrets, data files).
3. Create requirements.txt with pinned versions of all dependencies.
4. Implement the configuration loader (src/config_loader.py) that:
   - Reads YAML from config/settings.yaml
   - Loads environment variables from .env
   - Validates everything with Pydantic v2 ConfigSchema
   - Provides typed access to all config values
5. Create config/settings.yaml with all default values from the PRD.
6. Create config/.env.example with all required environment variables.
7. Create config/targets.csv template.
8. Write unit tests for the config loader.
9. Ensure all code passes mypy strict and has 80%+ coverage.

CONSTRAINTS:
- Do NOT proceed to the next task until I approve this one.
- One task at a time. Do not build ahead.
- Use Plan Mode first, then review the implementation plan before coding.
- Follow the eduig-build-phase workflow.
- Reference the web-scraper skill for Playwright patterns.
- Reference the api-patterns skill for HTTP client design.

DELIVERABLE:
- A working config system that I can test with: python -c "from src.config_loader import load_config; print(load_config())"
- All tests passing.
- A walkthrough artifact explaining the config system design.
```

---

## SECTION 3: PHASE-BY-PHASE PROMPT SEQUENCE

### Phase 1 Prompts (One Per Task)

**Task 1.1: Project Initialization**
```
TASK: Initialize Git repository, .gitignore, LICENSE (MIT for academic use), 
and README skeleton for EduIG-Pipeline.

RULES:
- .gitignore must exclude: venv/, data/, .env, __pycache__/, *.pyc, .pytest_cache/
- README must have sections: Overview, Install, Configure, Run, Test, Compliance
- Use the bash-scripting skill for any setup scripts.

OUTPUT: Working git repo with first commit.
```

**Task 1.2: Virtual Environment & Dependencies**
```
TASK: Create requirements.txt and a setup script (scripts/setup.sh) that:
- Creates Python 3.10+ virtual environment
- Installs all dependencies
- Installs Playwright Chromium browser
- Runs a quick health check

DEPENDENCIES TO INCLUDE:
playwright>=1.40.0, httpx>=0.25.0, pydantic>=2.0.0, schedule>=1.2.0,
structlog>=23.0.0, pandas>=2.0.0, polars>=0.19.0, pyyaml>=6.0.0,
python-dotenv>=1.0.0, pytest>=7.0.0, pytest-asyncio>=0.21.0,
matplotlib>=3.7.0, seaborn>=0.12.0, jupyter>=1.0.0

OUTPUT: setup.sh script that successfully installs everything.
```

**Task 1.3: Configuration System**
```
TASK: Build the configuration loader as described in the master prompt.
Use Pydantic v2 BaseModel for ConfigSchema with nested models for:
- RateLimitConfig (requests_per_hour, base_delay, max_retries, backoff_factor)
- PathsConfig (raw_data, processed, logs)
- ComplianceConfig (max_profiles_per_run, delete_raw_after_days, require_consent)

OUTPUT: src/config_loader.py with full validation and tests.
```

**Task 1.4: Structured Logger**
```
TASK: Implement src/logger.py using structlog with:
- JSON renderer for production
- Console renderer for development (configurable)
- Context binding for run_id, target, etc.
- Separate log files: app.log, error.log, audit.log
- Log rotation: daily, 7-day retention for app, 30-day for error, never for audit

OUTPUT: Working logger that can be imported and used across all modules.
```

**Task 1.5: First Browser Worker**
```
TASK: Implement src/browser_worker.py with a single function:
extract_public_profile(username: str) -> ProfileSchema

Use Playwright sync API with:
- Headless Chromium
- Viewport 1280x800
- Accept-Language header
- 3-second human-like delay
- page.evaluate() for JSON extraction (primary)
- CSS selector fallback
- Proper browser cleanup in finally block

Use the web-scraper skill for best practices.
Test with 5 public Instagram profiles.

OUTPUT: Working extraction that returns validated ProfileSchema.
```

---

### Phase 2 Prompts

**Task 2.1: Rate Limiter**
```
TASK: Implement src/rate_limiter.py with:
- LeakyBucket class (token bucket variant)
- wait() method with jitter (0.5-1.5x)
- Exponential backoff function
- Circuit breaker with states: CLOSED, OPEN, HALF-OPEN
- Daily request cap enforcement
- State persistence to SQLite between runs

Use async/await for all timing operations.
Write comprehensive unit tests with mocked time.

OUTPUT: RateLimiter that enforces 20 req/hour with full test coverage.
```

**Task 2.2: Router**
```
TASK: Implement src/router.py that:
- Accepts a Target object
- Checks for valid OAuth token
- Checks target consent_status
- Returns APIWorker or BrowserWorker instance
- Logs routing decision to audit log

Decision matrix:
- OAuth + consent -> APIWorker
- No OAuth / public -> BrowserWorker
- OAuth + no consent -> BrowserWorker (public only)
- Private + no auth -> Skip + log

OUTPUT: Router that correctly dispatches to appropriate worker.
```

**Task 2.3: Pydantic Schemas**
```
TASK: Implement src/schemas.py with Pydantic v2 models:
- ProfileSchema (profile_id, username_hash, bio, followers, following, posts_count, extracted_at, source)
- PostSchema (post_id, profile_id, caption, likes, comments, hashtags, posted_at, engagement_rate)
- RunSchema (run_id, started_at, completed_at, targets_count, success_count)
- AuditLogSchema (timestamp, target, action, status, bytes_collected, compliance_note)
- TargetSchema (username, url, consent_status, notes)

All models must have:
- Custom validators for data cleaning
- Config frozen=False (mutable for normalization)
- JSON serialization methods

OUTPUT: Complete schema module with tests.
```

**Task 2.4: Parser**
```
TASK: Implement src/parser.py with:
- parse_api_response(json_data: dict) -> RawData
- parse_browser_response(page_data: dict) -> RawData
- parse_post_data(media_list: list) -> list[PostSchema]
- Handle missing fields gracefully (None instead of KeyError)
- Convert string numbers ("1.2k") to integers
- Parse Instagram timestamps to ISO 8601

OUTPUT: Parser that handles both API and browser responses.
```

**Task 2.5: Normalizer**
```
TASK: Implement src/normalizer.py with:
- Schema mapping (API/browser fields -> internal schema)
- PII stripping:
  - SHA-256 hash for usernames
  - Regex removal of emails
  - Regex removal of phones
  - Anonymize location mentions
- Deduplication via MD5 hash
- Type coercion
- Pydantic validation

OUTPUT: Normalizer that produces clean, anonymized data.
```

**Task 2.6: SQLite Storage**
```
TASK: Implement src/storage.py with:
- SQLite connection manager with WAL mode
- Table creation SQL for: profiles, posts, runs, audit_log
- CRUD operations for all tables
- Atomic transactions
- CSV export functionality
- JSON raw data writer with metadata headers

Use context managers for all DB operations.
Write integration tests with in-memory SQLite.

OUTPUT: Storage module that persists all data formats.
```

**Task 2.7: Main Orchestrator**
```
TASK: Implement run.py that:
- Parses CLI arguments (--config, --dry-run, --resume, --export-csv)
- Loads configuration
- Initializes logger
- Reads targets.csv
- For each target:
  - Router.route() -> Worker
  - RateLimiter.wait()
  - Worker.execute()
  - Parser.parse()
  - Normalizer.normalize()
  - Storage.write()
  - AuditLogger.log()
- Runs compliance cleanup
- Generates summary report

Use async main() with asyncio.run().
Handle SIGINT/SIGTERM gracefully.

OUTPUT: Complete pipeline that runs end-to-end.
```

---

### Phase 3 Prompts

**Task 3.1: PII Stripper & Consent Tracker**
```
TASK: Implement src/compliance.py with:
- PIIStripper class with regex-based removal
- ConsentTracker that validates consent_status before API access
- RetentionEnforcer that deletes raw JSON after N days
- ExportController that verifies CSV exports have no PII
- AuditGenerator that produces compliance_report_{date}.md

Write tests that verify:
- Emails are removed from bios
- Phone numbers are removed
- Usernames are hashed
- Raw data is deleted after retention period
- Consent is checked before API calls

OUTPUT: Full compliance module with verification tests.
```

**Task 3.2: Error Handling & Resilience**
```
TASK: Enhance all workers with:
- Try/except/finally around all external calls
- Graceful degradation (partial data saved on failure)
- Resume capability (save run state to SQLite)
- Dry-run mode (validate without scraping)
- Detailed error logging with context

Update run.py to:
- Handle keyboard interrupt
- Save progress on unexpected exit
- Resume from last successful target

OUTPUT: Resilient pipeline that handles failures gracefully.
```

**Task 3.3: Integration Tests**
```
TASK: Write integration tests in tests/integration/ that:
- Mock Playwright and httpx
- Test full pipeline with 3 fake targets
- Verify rate limiting is enforced
- Verify data flows through all modules correctly
- Verify compliance rules are applied
- Verify audit logs are written

Use pytest fixtures for test isolation.
Use tmp_path for test data directories.

OUTPUT: Integration test suite that validates the entire pipeline.
```

---

### Phase 4 Prompts

**Task 4.1: Post Extraction**
```
TASK: Extend browser_worker.py to extract:
- 10 most recent posts per profile
- Post caption text
- Like count
- Comment count
- Timestamp
- Hashtag list (extracted from caption via regex)

Add to PostSchema and storage.
Calculate engagement_rate = (likes + comments) / followers.

Handle pagination truncation (Instagram limits public access).
Document limitation in code comments.

OUTPUT: Post extraction with engagement metrics.
```

**Task 4.2: Graph API Worker**
```
TASK: Implement src/api_worker.py with:
- OAuth 2.0 token management (refresh logic)
- httpx AsyncClient for API calls
- Endpoints: /me, /me/media, /{user-id}, /{media-id}
- Error handling for token expiry, permissions, quotas
- Rate limit tracking from API response headers

Only activate when OAuth token is present and consent is granted.

OUTPUT: API worker for consented accounts.
```

**Task 4.3: Jupyter Notebooks**
```
TASK: Create analysis notebooks in notebooks/:
- 01_exploratory_analysis.ipynb: Load data, basic stats, distributions
- 02_engagement_metrics.ipynb: Engagement rate analysis, correlations, visualizations
- 03_compliance_report.ipynb: Verify PII stripping, audit log analysis, retention compliance

Use pandas/polars for data manipulation.
Use matplotlib/seaborn for charts.
Include markdown explanations for academic context.

OUTPUT: Three ready-to-run analysis notebooks.
```

---

### Phase 5 Prompts

**Task 5.1: Documentation Polish**
```
TASK: Complete all documentation:
- README.md: Overview, install steps, config guide, run instructions, test commands, compliance notes, citation info
- CONTRIBUTING.md: Branch strategy, commit format, PR process, code review checklist
- Inline docstrings: Every public method
- Architecture diagrams: ASCII art in README

Ensure documentation is clear enough for another student to replicate.

OUTPUT: Professional documentation suite.
```

**Task 5.2: Final Verification**
```
TASK: Run complete verification:
1. pytest --cov=src --cov-fail-under=80
2. mypy src/ --strict
3. black src/ && isort src/
4. flake8 src/ --max-line-length=100
5. Run pipeline on 50 test profiles
6. Generate compliance report
7. Verify all artifacts

Fix any issues found.

OUTPUT: Passing verification with report.
```

---

## SECTION 4: CRITICAL INSTRUCTIONS FOR ANTIGRAVITY

### How to Work With This Prompt

1. **ALWAYS start in Plan Mode** - Do not write code until the implementation plan is reviewed and approved.
2. **ONE TASK AT A TIME** - Complete each task fully before moving to the next. Do not build ahead.
3. **USE THE WORKFLOWS** - Trigger `/eduig-build-phase` for each implementation task and `/eduig-test-and-verify` after completion.
4. **REFERENCE THE SKILLS** - Use the web-scraper, bash-scripting, api-patterns, and workflow-automation skills as needed.
5. **FOLLOW THE RULES** - The `.agents/rules/` files are non-negotiable. Any violation must be fixed immediately.
6. **GENERATE ARTIFACTS** - Every task must produce: Task List, Implementation Plan, Code Diffs, and Walkthrough.
7. **WAIT FOR APPROVAL** - After each task, pause and wait for human review before proceeding.

### Communication Protocol

| Situation | Action |
|-----------|--------|
| Task complete | Generate walkthrough artifact; pause for approval |
| Rule violation found | Stop immediately; report violation; suggest fix |
| Unclear requirement | Ask clarifying question; do not guess |
| Test failure | Fix before proceeding; do not skip tests |
| External dependency issue | Document workaround; suggest alternative |
| Compliance concern | Flag immediately; suggest mitigation |

### Skill Invocation Guide

| When You Need... | Invoke Skill |
|------------------|--------------|
| Web scraping patterns | `web-scraper` |
| Shell script setup | `bash-scripting` |
| API design decisions | `api-patterns` |
| Agent orchestration | `workflow-automation` |

### Model Selection Guide

| Task Type | Recommended Model |
|-----------|-------------------|
| Architecture planning | Gemini 3.1 Pro |
| Complex implementation | Claude Opus 4.6 |
| Quick fixes / refactoring | Gemini 3 Flash |
| Testing & verification | Claude Sonnet 4.6 |

---

## SECTION 5: APPROVAL CHECKPOINTS

After EACH task, the human must confirm:

- [ ] Code follows all AI_RULES.md constraints
- [ ] Tests pass with 80%+ coverage
- [ ] mypy strict passes
- [ ] No secrets in code
- [ ] Documentation updated
- [ ] Walkthrough artifact reviewed

**DO NOT PROCEED TO NEXT TASK UNTIL ALL CHECKBOXES ARE CHECKED.**

---

**End of PROMPT_FOR_ANTIGRAVITY**
