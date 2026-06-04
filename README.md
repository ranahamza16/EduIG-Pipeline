# EduIG-Pipeline

**EduIG-Pipeline** is a privacy-first, compliance-driven Instagram data extraction and normalization pipeline designed specifically for **academic researchers**. 

By leveraging both headless browser automation (Playwright) and the official Instagram Graph API, the pipeline safely extracts engagement metrics and public profile metadata while enforcing strict rate limiting and automatic Personally Identifiable Information (PII) stripping.

---

## ⚖️ Academic & Legal Disclaimer

> [!WARNING]
> **Strictly for Academic Research**  
> This software is built *exclusively* for academic research and social science studies. 
> 
> - **No Commercial Use**: Do not use this pipeline for marketing, lead generation, or spam.
> - **Respect Terms of Service**: Users are responsible for ensuring their usage complies with Instagram's [Terms of Use](https://help.instagram.com/581066165581870) and [Data Policy](https://help.instagram.com/519522125107875).
> - **Rate Limits**: The pipeline respects server load by enforcing conservative delays and daily caps. Do not disable the `RateLimiter`.
> - **Compliance**: The `ComplianceEngine` automatically scrubs emails and phone numbers from datasets. Maintain ethical research standards and obtain Institutional Review Board (IRB) approval where necessary.

---

## 🚀 Features

- **Dual-Engine Architecture**: 
  - `BrowserWorker`: Extracts data from public, unauthenticated profiles via DOM/JSON parsing.
  - `APIWorker`: Utilizes the official Graph API (`httpx`) for consented targets when an OAuth token is provided.
- **PII Scrubbing**: Automatically detects and replaces emails, phone numbers, and external links with `[EMAIL_REMOVED]`, etc.
- **SQLite Storage**: Atomically stores normalized metrics (`profiles` and `posts` tables) ready for immediate analysis.
- **Resilience**: Tracks execution state. If a crash occurs, use `--resume <RUN_ID>` to pick up exactly where you left off.
- **Jupyter Ready**: Includes boilerplate notebooks and a separate `requirements-research.txt` to help researchers chart data seamlessly using `pandas` and `seaborn`.

---

## 🛠️ Setup Instructions

### 1. Prerequisites
Ensure you have **Python 3.10+** installed.

### 2. Virtual Environment & Dependencies
Clone the repository and set up your Python virtual environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the core pipeline dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 3. (Optional) Research Dependencies
If you plan to run the included Jupyter analysis notebooks:
```bash
pip install -r requirements-research.txt
```

---

## ⚙️ Configuration Guide

The pipeline is primarily configured via `config/settings.yaml`. 

```yaml
rate_limit:
  requests_per_hour: 20
  base_delay: 5.0
  max_retries: 3
compliance:
  max_profiles_per_run: 50
  delete_raw_after_days: 7
  require_consent: false
browser:
  headless: true
```

### Environment Overrides (`.env`)
You can override any YAML configuration securely using a `.env` file at the project root. This is required for API functionality.

Copy the example file to get started:
```bash
cp .env.example .env
```

**Example `.env`**:
```ini
# Add your official Graph API Token if tracking consented users
EDUIG_API__ACCESS_TOKEN=your_oauth_token_here

# Override the rate limit directly
EDUIG_RATE_LIMIT__REQUESTS_PER_HOUR=30
```

---

## 🔐 Authentication Setup

To bypass aggressive CAPTCHAs and account locks, EduIG-Pipeline uses **Cookie Injection** instead of automated password typing.

### 1. Capture Your Session
Run the interactive cookie extractor. This will open a visible Chromium browser:
```bash
python src/auth/cookie_extractor.py
```
- Log in manually to Instagram.
- Complete any 2FA or security checks.
- Once you reach the homepage, the script will automatically save your session cookies and `localStorage` to `data/session_cookies.json` and close the browser.

### 2. Running the Authenticated Scraper
With cookies saved, run the pipeline in authenticated mode. It will inject your cookies into a stealth headless browser to fetch precise counts via the internal JSON API.

To securely test the exact-count extraction logic against a single target (outputs to `data/artifacts/`):
```bash
python scripts/test_authenticated_extraction.py <optional_target_username>
```

To run the full multi-target extraction pipeline with authentication enabled (pulling exact unrounded data):
```bash
python run.py --authenticated
```

To run a rapid authentication test through the pipeline entrypoint without executing a full run:
```bash
python run.py --test-login
```

### Detailed Usage Guide
For a comprehensive, step-by-step tutorial on how to use the pipeline from start to finish, please refer to the [How to Use Guide](How_to_use.md).

### Anti-Detection Measures
The pipeline implements the following protections:
- **Stealth Browser**: Overrides `playwright` fingerprints, CDP, and `navigator` APIs.
- **Fingerprint Consistency**: Ties hardware concurrency and locales deterministically to your username.
- **Human-like Behavior**: Uses Bezier-curve mouse movements and variable typing delays.

> [!NOTE]
> Even with stealth measures, you should restrict authenticated scraping to a maximum of **50 requests/day** and **20 requests/hour** to prevent soft bans.

---

## 📈 Dashboard

Launch the local dashboard with: `make dashboard` or `python run.py --dashboard`

The dashboard is READ-ONLY — it visualizes data from `data/eduig.db`.
No Instagram credentials required to view the dashboard.

Features: real-time stats, profile search, compliance reports, CSV export.
![Dashboard Overview](docs/dashboard_screenshot.png)

PWA: Installable on mobile/desktop, works offline with cached data.

---

## 🎯 Usage Examples

### 1. Define Your Targets
Add the Instagram handles or shortcodes you wish to study to `config/targets.csv`. 
You can specify an optional `consent_status` boolean for each target to route them through the official Graph API (if an `ACCESS_TOKEN` is configured).

```csv
# format: URL, consent_status
rana_hamza16, false
https://instagram.com/academic_study_user, true
```

### 2. Dry Run
Always validate your targets and configuration before sending real network requests.

```bash
python run.py --dry-run
```

### 3. Execute Pipeline
Run the full extraction pipeline. Logs are piped securely to `data/logs/` and outputs go to `data/eduig.db`.

```bash
python run.py
```

To execute a run and automatically export the database into perfectly formatted, human-readable `.csv` files:
```bash
python run.py --authenticated --export-csv
```

### 4. Resume an Interrupted Run
If the script is halted due to a rate limit or user interruption, find your `RUN_ID` in the logs and resume:

```bash
python run.py --resume "your-uuid-run-id"
```

---

## 📊 Data Analysis

Once you have gathered your dataset, launch Jupyter Notebook to analyze the engagement metrics.

```bash
jupyter notebook notebooks/01_engagement_analysis.ipynb
```

The example notebook demonstrates how to load the SQLite `profiles` and `posts` tables into `pandas` DataFrames and visualize correlations between follower counts and engagement rates.
