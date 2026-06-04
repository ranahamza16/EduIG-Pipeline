# Technical Architecture Document
## EduIG-Pipeline: System Design & Module Breakdown

**Version:** 1.0  
**Date:** 2026-05-31  
**Authors:** [Student Team]  
**Status:** Draft - Ready for Development  

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

EduIG-Pipeline follows a layered, modular pipeline architecture with clear separation of concerns:

```
+-----------------------------------------------------------------+
|                      CONFIGURATION LAYER                        |
|              (YAML Settings, Environment Variables)             |
+-----------------------------------------------------------------+
|                      ORCHESTRATION LAYER                        |
|              (Task Scheduler, Main Entry Point)                 |
+-----------------------------------------------------------------+
|                        ROUTING LAYER                            |
|         (Auth Detection -> API Worker or Browser Worker)        |
+-----------------------------------------------------------------+
|                      ACQUISITION LAYER                          |
|    +---------------------+    +-----------------------------+    |
|    |   Official API      |    |   Browser Automation        |    |
|    |   (Graph API)       |    |   (Playwright)              |    |
|    |   - OAuth 2.0       |    |   - Headless Chromium       |    |
|    |   - Consented Data  |    |   - Public Profile Extraction|   |
|    |   - Business Metrics|    |   - Post Metadata           |    |
|    +---------------------+    +-----------------------------+    |
+-----------------------------------------------------------------+
|                      PROTECTION LAYER                           |
|         (Rate Limiter, Retry Logic, Jitter, Backoff)            |
+-----------------------------------------------------------------+
|                      PROCESSING LAYER                           |
|         (Parser, Validator, Normalizer, Deduplicator)          |
+-----------------------------------------------------------------+
|                      PERSISTENCE LAYER                          |
|    +--------------+  +--------------+  +------------------+    |
|    |   SQLite     |  |    JSON      |  |      CSV         |    |
|    |  (Primary)   |  |   (Raw)      |  |  (Processed)     |    |
|    +--------------+  +--------------+  +------------------+    |
+-----------------------------------------------------------------+
|                      OBSERVABILITY LAYER                        |
|         (Structured Logging, Audit Trail, Error Tracking)       |
+-----------------------------------------------------------------+
|                      COMPLIANCE LAYER                           |
|         (Data Retention, PII Stripping, Consent Tracking)       |
+-----------------------------------------------------------------+
```

### 1.2 Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Local-First** | All processing on student laptop; no cloud dependencies |
| **Zero-Cost** | Only open-source tools and free tiers |
| **Compliance-by-Design** | Every module has audit hooks; data minimization enforced |
| **Fail-Safe** | Graceful degradation; partial data preserved on failure |
| **Modular** | Each layer can be tested/replaced independently |
| **Observable** | Every operation logged with structured, queryable output |

---

## 2. Module-by-Module Breakdown

### 2.1 Configuration Layer (config/)

| File | Purpose | Schema |
|------|---------|--------|
| targets.csv | List of Instagram usernames/URLs to scrape | username, url, consent_status, notes |
| settings.yaml | All tunable parameters | See Section 4.1 |
| .env (gitignored) | Sensitive values: OAuth tokens, API keys | INSTAGRAM_ACCESS_TOKEN, CLIENT_ID |

**Responsibilities:**
- Load and validate configuration at startup
- Provide typed config objects to all modules
- Hot-reload support (optional future enhancement)

---

### 2.2 Orchestration Layer (run.py, scheduler/)

| Component | File | Responsibility |
|-----------|------|----------------|
| Main Entry Point | run.py | Parse CLI args, load config, initialize pipeline, execute runs |
| Task Scheduler | src/scheduler.py | schedule library integration; cron-like execution; run windows |
| Run Manager | src/run_manager.py | Track run state (start, progress, completion, failure); resume support |

**Execution Flow:**
```
run.py -> Load Config -> Initialize Logger -> Load Targets -> 
  For each target:
    -> Router.decide() -> RateLimiter.wait() -> Worker.execute() -> 
    -> Parser.parse() -> Normalizer.normalize() -> Storage.write() -> 
    -> AuditLogger.log() -> ComplianceChecker.verify()
  -> Cleanup & Retention -> Generate Report
```

---

### 2.3 Routing Layer (src/router.py)

```python
class Router:
    def __init__(self, config):
        self.api_worker = APIWorker(config)
        self.browser_worker = BrowserWorker(config)

    def route(self, target: Target) -> Worker:
        # Decide which worker to use based on auth and target type
        if self.has_valid_oauth() and target.consent_status == "granted":
            return self.api_worker
        return self.browser_worker
```

**Decision Matrix:**

| Condition | API Worker | Browser Worker |
|-----------|------------|----------------|
| Valid OAuth token + consent | Yes | No |
| No OAuth / public profile | No | Yes |
| OAuth token but no consent | No | Yes (public only) |
| Private profile (no auth) | No | No (skip + log) |

---

### 2.4 Acquisition Layer

#### 2.4.1 API Worker (src/api_worker.py)

| Aspect | Detail |
|--------|--------|
| Protocol | HTTPS REST via httpx |
| Auth | OAuth 2.0 Bearer token (Meta Graph API) |
| Endpoints | /me, /me/media, /{user-id}, /{media-id} |
| Rate Limit | 200 calls/hour/user (Meta's limit, we enforce 20) |
| Data Types | Business/creator metrics, insights, stories (with consent) |
| Error Handling | Token expiry refresh, permission errors, quota exceeded |

**Key Methods:**
- async def get_user_profile(self, user_id: str) -> dict
- async def get_user_media(self, user_id: str, limit: int = 10) -> list[dict]
- async def get_media_insights(self, media_id: str) -> dict

#### 2.4.2 Browser Worker (src/browser_worker.py)

| Aspect | Detail |
|--------|--------|
| Engine | Playwright (Chromium) |
| Mode | Headless (headless=True) |
| Viewport | 1280x800 (desktop, less bot-like than default) |
| Headers | Accept-Language: en-US,en;q=0.9 |
| Strategy | page.evaluate() JavaScript injection for JSON extraction |
| Fallback | CSS selector extraction if JSON fails |
| Cleanup | Browser context isolation; explicit browser.close() |

**Extraction Strategy:**
```python
def extract_public_profile(self, username: str) -> ProfileSchema:
    page.goto(f"https://instagram.com/{username}/")
    page.wait_for_timeout(3000)  # Human-like delay

    # Primary: JSON extraction from page scripts
    data = page.evaluate("window._sharedData?.entry_data?.ProfilePage[0]")

    # Fallback: DOM scraping
    if not data:
        data = self._fallback_dom_extraction(page)

    return ProfileSchema(**data)
```

---

### 2.5 Protection Layer (src/rate_limiter.py)

**Components:**

| Component | Algorithm | Parameters |
|-----------|-----------|------------|
| Leaky Bucket | Token bucket variant | requests_per_hour: 20, min_interval: 180s |
| Jitter | Random uniform | jitter_range: [0.5, 1.5] |
| Exponential Backoff | base * 2^attempt + random(0,2) | base: 5s, max_retries: 3 |
| Circuit Breaker | Open after 5 consecutive failures | failure_threshold: 5, cooldown: 3600s |
| Daily Cap | Hard stop at N requests/day | max_requests_per_day: 50 |

**State Machine:**
```
[Closed] --failure--> [Half-Open] --success--> [Closed]
    ^                      |
    +---- cooldown ---------+
```

---

### 2.6 Processing Layer

#### 2.6.1 Parser (src/parser.py)

| Method | Input | Output | Validation |
|--------|-------|--------|------------|
| parse_api_response() | JSON (Graph API) | RawData dict | JSON schema validation |
| parse_html_response() | HTML/JSON (Playwright) | RawData dict | Field presence check |
| parse_post_data() | Media JSON | PostSchema list | Caption length, engagement numeric |

#### 2.6.2 Normalizer (src/normalizer.py)

| Operation | Description |
|-----------|-------------|
| Schema Mapping | Map API fields to internal schema (e.g., edge_followed_by.count -> followers) |
| Type Coercion | Convert string numbers ("1.2k") to integers; parse dates to ISO 8601 |
| Deduplication | MD5 hash of (username, timestamp); skip if exists in DB |
| PII Stripping | Hash usernames; remove bio emails/phone numbers; anonymize locations |
| Validation | Pydantic BaseModel validation with custom validators |

**Internal Schema (Pydantic):**
```python
class ProfileSchema(BaseModel):
    profile_id: str          # Hashed username
    username_hash: str       # SHA-256 of username
    bio: str | None          # Sanitized bio text
    followers: int | None
    following: int | None
    posts_count: int | None
    extracted_at: datetime
    source: Literal["api", "browser"]

class PostSchema(BaseModel):
    post_id: str
    profile_id: str
    caption: str | None
    likes: int | None
    comments: int | None
    hashtags: list[str]
    posted_at: datetime | None
    engagement_rate: float | None
```

---

### 2.7 Persistence Layer (src/storage.py)

#### 2.7.1 SQLite (Primary)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| profiles | Normalized profile data | profile_id, followers, following, posts_count, extracted_at |
| posts | Normalized post data | post_id, profile_id, likes, comments, engagement_rate |
| runs | Execution metadata | run_id, started_at, completed_at, targets_count, success_count |
| audit_log | Compliance trail | timestamp, target, action, status, bytes_collected, compliance_note |

**Configuration:**
```sql
PRAGMA journal_mode = WAL;       -- Write-Ahead Logging for concurrent access
PRAGMA foreign_keys = ON;        -- Enforce referential integrity
PRAGMA synchronous = NORMAL;     -- Balance safety and speed
```

#### 2.7.2 JSON (Raw Archive)

| Aspect | Detail |
|--------|--------|
| Purpose | Preserve original API/browser responses for debugging/reproducibility |
| Structure | data/raw/{run_id}/{username}_{timestamp}.json |
| Retention | Auto-deleted after delete_raw_after_days (default: 7) |
| Format | Pretty-printed, UTF-8, with metadata header |

#### 2.7.3 CSV (Processed Export)

| Aspect | Detail |
|--------|--------|
| Purpose | Academic analysis import (R, SPSS, Excel, Pandas) |
| Structure | data/processed/profiles_{run_id}.csv, posts_{run_id}.csv |
| Encoding | UTF-8 with BOM for Excel compatibility |
| Anonymization | No raw usernames; only hashed IDs |

---

### 2.8 Observability Layer (src/logger.py)

**Structured Logging with structlog:**

```python
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

# Example log entry:
{
    "timestamp": "2026-05-31T18:39:00Z",
    "event": "profile_extracted",
    "target": "example_user",
    "source": "browser",
    "status": "success",
    "bytes_collected": 2048,
    "compliance_note": "public_data_only",
    "run_id": "run_20260531_001"
}
```

**Log Files:**

| File | Content | Rotation |
|------|---------|----------|
| data/logs/app.log | All structured logs | Daily, 7-day retention |
| data/logs/error.log | ERROR+ level only | Daily, 30-day retention |
| data/logs/audit.log | Compliance events only | Never auto-delete (manual purge) |

---

### 2.9 Compliance Layer (src/compliance.py)

| Component | Responsibility |
|-----------|----------------|
| Consent Tracker | Verify consent_status in targets.csv before API access |
| PII Stripper | Remove/anonymize PII before storage; regex for emails, phones, URLs |
| Retention Enforcer | Scheduled cleanup of raw JSON; SQLite vacuum |
| Export Controller | Ensure exported CSVs contain no PII; hash all identifiers |
| Audit Generator | Produce compliance report: compliance_report_{date}.md |

---

## 3. Data Flow & Interactions

### 3.1 Happy Path Flow

```
+----------+     +----------+     +----------+     +----------+
| targets  |---->|  Router  |---->|  Worker  |---->|  Parser  |
|  .csv    |     |          |     |(API/Browser)|   |          |
+----------+     +----------+     +----------+     +-----+----+
                                                        |
                              +-------------------------+
                              v
+----------+     +----------+     +----------+     +----------+
|  Audit   |<----|  Storage |<----| Normalizer|<----| Validator|
|  Log     |     |(SQLite/  |     |          |     |(Pydantic)|
|          |     |JSON/CSV) |     |          |     |          |
+----------+     +----------+     +----------+     +----------+
```

### 3.2 Error Handling Flow

```
Worker Failure -> Exponential Backoff (3 retries)
    |
    +-> Success -> Continue pipeline
    |
    +-> Max retries exceeded -> Log error -> Skip target -> Continue
            |
            +-> 5 consecutive failures -> Circuit Breaker OPEN -> 
                Pause 1 hour -> Half-Open test -> Close on success
```

### 3.3 Compliance Flow

```
Raw Data -> PII Stripper -> Anonymized Data -> Storage
    |                           |
    +-> Raw JSON (7-day)        +-> SQLite (permanent, anonymized)
    |                           |
    +-> Auto-delete after 7d    +-> CSV Export (anonymized)
```

---

## 4. Technology Stack Decisions

### 4.1 Core Stack

| Layer | Technology | Version | Justification |
|-------|-----------|---------|---------------|
| Language | Python | 3.10+ | Universally taught; excellent scraping ecosystem; type hints |
| Browser Automation | Playwright | Latest | Microsoft-backed; reliable; handles modern JS; auto-waits |
| HTTP Client | httpx | Latest | Async support; HTTP/2; timeout handling; retry built-in |
| Data Validation | Pydantic | v2 | Runtime validation; JSON serialization; type safety |
| Scheduling | schedule | Latest | Simple cron-like syntax; no external dependencies |
| Logging | structlog | Latest | Structured JSON logs; context binding; performance |
| Storage (Primary) | SQLite | Built-in | Zero config; ACID; WAL mode; portable |
| Data Analysis | pandas, polars | Latest | Academic standard; CSV/Parquet export; visualization |
| Config | PyYAML | Latest | Human-readable; comments; nested structures |

### 4.2 Alternative Considerations

| Alternative | Why Not Chosen |
|-------------|----------------|
| Selenium | Heavier; slower; more detection-prone than Playwright |
| Scrapy | Overkill for single-machine, low-volume project |
| PostgreSQL | Requires setup; SQLite is sufficient for academic scale |
| MongoDB | Overkill; SQLite handles structured schema better |
| Airflow | Too complex for 2-student, single-machine project |
| Celery | No distributed needs; schedule is sufficient |

---

## 5. File Structure & Dependencies

### 5.1 Project Structure

```
EduIG-Pipeline/
|
+-- config/
|   +-- targets.csv              # Research targets list
|   +-- settings.yaml            # All configuration
|   +-- .env.example             # Template for env vars
|
+-- src/
|   +-- __init__.py
|   +-- router.py                # Request routing logic
|   +-- api_worker.py            # Meta Graph API client
|   +-- browser_worker.py        # Playwright automation
|   +-- rate_limiter.py          # Rate limiting & backoff
|   +-- parser.py                # Response parsing
|   +-- normalizer.py            # Data normalization & PII stripping
|   +-- storage.py               # SQLite/JSON/CSV persistence
|   +-- compliance.py            # Compliance checks & retention
|   +-- logger.py                # Structured logging setup
|   +-- scheduler.py             # Execution scheduling
|   +-- run_manager.py           # Run lifecycle management
|   +-- schemas.py               # Pydantic models
|
+-- data/
|   +-- raw/                     # Original responses (7-day retention)
|   +-- processed/               # Normalized CSV/Parquet
|   +-- logs/                    # Application & audit logs
|
+-- notebooks/
|   +-- 01_exploratory_analysis.ipynb
|   +-- 02_engagement_metrics.ipynb
|   +-- 03_compliance_report.ipynb
|
+-- tests/
|   +-- test_rate_limiter.py
|   +-- test_parser.py
|   +-- test_normalizer.py
|   +-- test_storage.py
|
+-- run.py                       # Main entry point
+-- requirements.txt             # Python dependencies
+-- README.md                    # Project documentation
+-- .gitignore                   # Git ignore rules
+-- LICENSE                      # Academic use license
```

### 5.2 Dependency Graph

```
run.py
+-- src/router.py
|   +-- src/api_worker.py
|   |   +-- httpx
|   |   +-- src/schemas.py
|   +-- src/browser_worker.py
|       +-- playwright
|       +-- src/schemas.py
+-- src/rate_limiter.py
|   +-- (stdlib: time, random)
+-- src/parser.py
|   +-- src/schemas.py
+-- src/normalizer.py
|   +-- pydantic
|   +-- src/schemas.py
+-- src/storage.py
|   +-- sqlite3 (stdlib)
|   +-- pandas
|   +-- src/schemas.py
+-- src/compliance.py
|   +-- src/storage.py
+-- src/logger.py
|   +-- structlog
+-- src/scheduler.py
|   +-- schedule
+-- src/run_manager.py
    +-- src/logger.py
```

### 5.3 requirements.txt

```
# Core
playwright>=1.40.0
httpx>=0.25.0
pydantic>=2.0.0

# Scheduling & Orchestration
schedule>=1.2.0

# Logging
structlog>=23.0.0

# Data Processing
pandas>=2.0.0
polars>=0.19.0

# Configuration
pyyaml>=6.0.0
python-dotenv>=1.0.0

# Testing
pytest>=7.0.0
pytest-asyncio>=0.21.0

# Analysis (optional, for notebooks)
matplotlib>=3.7.0
seaborn>=0.12.0
jupyter>=1.0.0
```

---

## 6. Deployment & Execution

### 6.1 Local Development

```bash
# 1. Clone & setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. Configure
cp config/.env.example config/.env
# Edit config/settings.yaml and config/targets.csv

# 3. Run
python run.py --config config/settings.yaml
```

### 6.2 Execution Modes

| Mode | Command | Use Case |
|------|---------|----------|
| Single Run | python run.py | Manual execution; testing |
| Scheduled | python run.py --schedule daily | Cron-like daily runs |
| Dry Run | python run.py --dry-run | Validate config without scraping |
| Resume | python run.py --resume run_20260531_001 | Resume interrupted run |
| Export Only | python run.py --export-csv | Generate CSV from existing SQLite |

---

**End of Architecture Document**
