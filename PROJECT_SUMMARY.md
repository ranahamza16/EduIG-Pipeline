# Project Summary: EduIG-Pipeline

## What Was Built
**EduIG-Pipeline** is a privacy-first, ethically engineered Instagram data scraper designed exclusively for academic and institutional research. It securely extracts public data, mathematically anonymizes personal identifiers, strictly strips out Personally Identifiable Information (PII), and stores normalized data in an ACID-compliant local SQLite database.

## Key Features
- **Dual Engine Extraction**: Uses an asynchronous `Playwright` browser worker for public profiles and an `httpx` API worker for accounts with explicit academic consent.
- **Strict Anonymization & PII Stripping**: Automatically SHA-256 hashes usernames, strips emails/phone numbers via regex, and anonymizes identifying traits from raw JSONs before data is persisted.
- **Robust Orchestration**: Includes persistent circuit breakers, granular rate limiters (leaky bucket), and resilient resume logic that allows recovering pipelines from unexpected network errors.
- **Full Compliance Audit Trail**: Generates automated, IRB-ready markdown audit logs and compliance reports summarizing retention constraints, consent checks, and dataset sanitization status.
- **Analytical Readiness**: Delivers out-of-the-box Jupyter Notebooks (EDA, Engagement Metrics, Compliance Analytics) for immediate academic research insights.

## Technology Stack
- **Language**: Python 3.10+
- **Browser Automation**: `playwright` (Chromium, Async)
- **API Requests**: `httpx`
- **Data Validation & Typing**: `pydantic` (v2), Strict `mypy` typing
- **Logging**: `structlog` (JSON output)
- **Storage**: `sqlite3` (WAL-mode configured for concurrency)
- **Analysis**: `pandas`, `polars`, `jupyter`
- **Testing**: `pytest`, `pytest-cov`, `pytest-asyncio`
- **Code Quality**: `black`, `isort`, `flake8`

## How To Use
1. Set up the environment:
   ```bash
   bash scripts/setup.sh
   source venv/bin/activate
   ```
2. Populate `config/targets.csv` with the desired target usernames.
3. Execute the pipeline:
   ```bash
   # Dry-run execution to validate config and targets
   python run.py --dry-run
   
   # Standard extraction pipeline
   python run.py
   
   # If interrupted, safely resume with:
   python run.py --resume <run_id>
   ```
4. Output can be dumped directly into standard formats:
   ```bash
   python run.py --export-csv
   ```
   
## Known Limitations
- The `Playwright` engine depends on Instagram DOM structures, which are prone to silent unannounced changes that might break selectors.
- API endpoints are heavily rate-limited; attempting to extract without a significant backoff delay can lead to permanent institutional IP blocks.
- Post-extraction relies strictly on public-facing JSON and skips paginated "Reels" / IGTV components.

## Future Improvements
- **Proxies & Rotations**: Integrations with rotating residential IP proxies for large-scale multi-month scraping tasks without 429 errors.
- **Multimodal AI OCR**: Scraping specific frames or text natively overlayed on images/reels directly via vision-models.
- **Graph Networking Maps**: Storing follower/following intersection graphs in a specialized graph database (like Neo4j) to study academic networks.
