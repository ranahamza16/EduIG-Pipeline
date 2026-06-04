"""Interactive Cookie Extractor for Instagram.

This script launches a visible stealth browser for the user to log in manually.
Once logged in, it extracts cookies and localStorage, saving them for the pipeline.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta

from playwright.async_api import async_playwright

from src.auth.fingerprint_manager import FingerprintManager
from src.auth.stealth_browser import StealthBrowser

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cookie_extractor")

COOKIE_FILE = "data/session_cookies.json"


async def extract_cookies() -> None:
    """Launch visible browser, wait for login, and extract session data."""
    # 1. Setup fingerprint and stealth browser
    username = os.getenv("INSTAGRAM_USERNAME", "cookie_extractor")
    fingerprint = FingerprintManager(username).generate()
    
    # We pass a simple logger dict-like object if StealthBrowser expects it, 
    # but StealthBrowser uses default_logger if none provided.
    browser_manager = StealthBrowser(fingerprint)
    
    logger.info("Launching visible browser. Please log in manually.")
    
    # Launch headless=False so user can see and interact
    context = await browser_manager.launch(headless=False)
    page = await browser_manager.new_page()

    # 2. Navigate to login
    await page.goto("https://www.instagram.com/accounts/login/")
    
    print("\n" + "="*60)
    print(">>> ACTION REQUIRED <<<")
    print("1. Please log into Instagram in the browser window.")
    print("2. Complete any 2FA or CAPTCHA challenges if prompted.")
    print("3. Wait here... I am monitoring for a successful login.")
    print("="*60 + "\n")

    # 3. Poll for successful login detection
    is_logged_in = False
    max_retries = 150  # 5 minutes (150 * 2 seconds)
    
    for attempt in range(max_retries):
        current_url = page.url
        
        # Check URL
        if "/direct/inbox/" in current_url or (current_url == "https://www.instagram.com/" or current_url == "https://www.instagram.com/?variant=following"):
             is_logged_in = True
             
        # Check DOM for profile icon or "Home" SVG
        if not is_logged_in:
            try:
                # Common elements present only when logged in
                if await page.query_selector('img[alt*="profile picture"]') or await page.query_selector('svg[aria-label="Home"]'):
                    is_logged_in = True
            except Exception:
                pass
                
        if is_logged_in:
            logger.info("Login detected! Extracting session data...")
            break
            
        await asyncio.sleep(2)
        
    if not is_logged_in:
        logger.error("Timeout waiting for login. Extraction aborted.")
        await browser_manager.close()
        return

    # 4. Extract session data
    # Wait a bit for all post-login cookies/storage to settle
    await asyncio.sleep(3)
    
    cookies = await context.cookies()
    
    # Extract localStorage and sessionStorage
    local_storage = await page.evaluate("() => JSON.stringify(window.localStorage)")
    session_storage = await page.evaluate("() => JSON.stringify(window.sessionStorage)")
    
    # Extract specific required values for verification
    ig_www_claim = "0"
    try:
        ls_dict = json.loads(local_storage)
        ig_www_claim = ls_dict.get("ig_www_claim", "0")
    except Exception:
        pass

    csrftoken = next((c["value"] for c in cookies if c["name"] == "csrftoken"), None)
    
    # Ensure sameSite is present in all cookies
    for cookie in cookies:
        if "sameSite" not in cookie:
            cookie["sameSite"] = "Lax" # Default fallback
            
    # 5. Save to file
    session_data = {
        "cookies": cookies,
        "localStorage": json.loads(local_storage),
        "sessionStorage": json.loads(session_storage),
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "expires_warning": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z",
        "meta": {
            "has_csrftoken": csrftoken is not None,
            "has_ig_www_claim": ig_www_claim != "0"
        }
    }
    
    os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
    with open(COOKIE_FILE, "w") as f:
        json.dump(session_data, f, indent=2)
        
    print("\n" + "="*60)
    print("SUCCESS! Cookies and local storage saved.")
    print(f"Session valid until: ~{session_data['expires_warning']}")
    print(f"File: {COOKIE_FILE}")
    print("="*60 + "\n")
    
    # 6. Wait for user dismissal
    input("Press Enter to close the browser and exit...")
    
    await browser_manager.close()
    logger.info("Browser closed.")

if __name__ == "__main__":
    try:
        asyncio.run(extract_cookies())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
