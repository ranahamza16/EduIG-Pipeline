# How to Use EduIG-Pipeline

EduIG-Pipeline is a data extraction and analysis tool for academic research. Follow this step-by-step guide to extract Instagram profile data accurately while respecting rate limits and anti-detection mechanisms.

## Step 1: Configure Your Environment

1. **Activate the Virtual Environment:**
   Before running any scripts, ensure your Python virtual environment is activated:
   ```bash
   source venv/bin/activate
   ```
   *(On Windows, use `venv\Scripts\activate`)*

2. **Set Your Targets:**
   Open `config/targets.csv` and add the usernames you want to scrape.
   ```csv
   # Example config/targets.csv
   abdul.mueez.shahid
   ayan_shibli
   natgeo
   ```

3. **Check Your Settings:**
   Review `config/settings.yaml` to ensure your rate limits and anti-detection delays are appropriate. The default settings (20 requests per hour, max 50 per day) are highly recommended to prevent your account from being locked or shadow-banned.

## Step 2: Extract Your Session Cookies

Because Instagram aggressively blocks automated requests, EduIG-Pipeline requires a real logged-in session to access exact post counts, likes, and comments. We use a **Cookie Injection** mechanism to securely bypass CAPTCHAs.

1. **Run the Cookie Extractor:**
   Launch the interactive cookie extractor tool:
   ```bash
   python src/auth/cookie_extractor.py
   ```

2. **Log In Manually:**
   - A visible Chromium browser window will open.
   - Enter your Instagram credentials and log in.
   - Complete any 2FA or security checks required by Instagram.

3. **Wait for Auto-Detection:**
   - Once you successfully reach the homepage, the script will automatically detect the login.
   - It securely extracts all essential cookies (including `sessionid` and `csrftoken`) and saves them to `data/session_cookies.json`.
   - The browser window will close automatically once the session is captured.

*Note: You only need to perform Step 2 once, or whenever your session expires (typically lasts a few days to weeks depending on usage).*

## Step 3: Run the Extraction Pipeline

With your session established and your targets defined, you can now run the pipeline in headless mode. 

1. **Execute the Pipeline with Authentication:**
   ```bash
   python run.py --authenticated --config config/settings.yaml
   ```

2. **What Happens Behind the Scenes:**
   - The pipeline launches a Stealth Playwright browser.
   - It seamlessly injects your saved cookies to authenticate.
   - For each target, it fetches precise profile stats, exact follower/following counts, and recent posts containing likes, comments, and hashtags.
   - Private accounts are appropriately detected, skipped for post extraction, and labeled as `[Private Account]` to prevent errors.
   - Data is cleaned (PII scrubbed) and stored atomically in the SQLite database (`data/eduig.db`).

## Step 4: Visualize and Export the Data

Once the extraction is complete, you can review your data through the built-in Flask Dashboard.

1. **Start the Dashboard:**
   ```bash
   make dashboard
   ```
   *Note: If `make` is unavailable, you can run `PYTHONPATH=. python src/dashboard/app.py`.*

2. **Access the Interface:**
   Open your web browser and navigate to: [http://localhost:5000](http://localhost:5000)

3. **Explore the Results:**
   - **Overview:** View real-time analytics, charts, and extraction statuses.
   - **Profiles:** Browse the list of successfully extracted targets.
   - **Profile Details:** Click on any public profile to see a grid of their most recent posts, including exact engagement metrics.

4. **Export Dataset:**
   To export the database into a perfectly formatted, human-readable CSV for your research tools (like pandas or R):
   - Click the **"Export CSV"** button on the dashboard.
   - Alternatively, you can trigger a CSV export from the command line:
     ```bash
     python run.py --authenticated --export-csv
     ```

## Tips for Safe Research
- **Respect Rate Limits:** Do not lower the base delays or increase the hourly requests beyond the defaults. Aggressive scraping will result in immediate bans.
- **Data Anonymization:** Use the PII scrubber (enabled in `settings.yaml` under `compliance.anonymize_pii`) before sharing your dataset with other researchers.
- **Handling Private Profiles:** Private accounts will successfully yield their exact follower/following counts, but post data will be returned as 0 unless your authenticated account explicitly follows them.
