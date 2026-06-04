# Web Scraper Skill
## Multi-Strategy Web Scraping with Playwright

---

## Overview

This skill provides guidance for building robust, ethical web scrapers using **Playwright** for browser automation. It covers stealth techniques, extraction strategies, error handling, and compliance patterns specifically for the EduIG-Pipeline project.

---

## Core Rules (Non-Negotiable)

- **Always use Playwright** — never Selenium, BeautifulSoup-only, or urllib
- **Always use `sync_playwright()` context manager** with `browser.close()` in `finally`
- **Never bypass authentication** — public data only
- **Always rate-limit** — never make back-to-back requests without delay
- **Always log** every extraction attempt to the audit trail

---

## Pattern 1: Basic Profile Extraction

```python
from playwright.sync_api import sync_playwright, Page
import structlog

logger = structlog.get_logger()

def extract_public_profile(username: str) -> dict:
    """Extract public Instagram profile using Playwright.
    
    Args:
        username: Instagram username (without @)
        
    Returns:
        Raw profile data dict. Empty dict on failure.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
            )
            page = context.new_page()
            
            # Navigate with human-like delay
            page.goto(f"https://www.instagram.com/{username}/", timeout=30000)
            page.wait_for_timeout(3000)  # Human-like delay
            
            # Strategy 1: JSON extraction from page scripts (PRIMARY)
            data = page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/json"]');
                    for (const script of scripts) {
                        try {
                            const json = JSON.parse(script.textContent);
                            if (json?.require) return json;
                        } catch(e) {}
                    }
                    return null;
                }
            """)
            
            if data:
                logger.info("profile_extracted", username=username, strategy="json")
                return data
            
            # Strategy 2: CSS selector fallback
            data = _fallback_dom_extraction(page, username)
            logger.info("profile_extracted", username=username, strategy="dom_fallback")
            return data
            
        except Exception as e:
            logger.error("extraction_failed", username=username, error=str(e))
            return {}
        finally:
            browser.close()


def _fallback_dom_extraction(page: Page, username: str) -> dict:
    """CSS selector fallback when JSON extraction fails."""
    return {
        "username": username,
        "followers": _safe_text(page, "meta[name='description']"),
        "bio": _safe_text(page, "div.-vDIg span"),
    }


def _safe_text(page: Page, selector: str) -> str | None:
    """Safely extract text from selector, returns None if not found."""
    try:
        element = page.query_selector(selector)
        return element.inner_text() if element else None
    except Exception:
        return None
```

---

## Pattern 2: Stealth Configuration

```python
def create_stealth_context(browser):
    """Create a browser context with anti-detection settings."""
    return browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
        },
        java_script_enabled=True,
        ignore_https_errors=False,
    )
```

---

## Pattern 3: Robust Wait Strategy

```python
def wait_for_content(page: Page, timeout: int = 10000) -> bool:
    """Wait for page content to fully load.
    
    Returns True if content loaded, False if timeout.
    """
    try:
        # Wait for network idle (no requests for 500ms)
        page.wait_for_load_state("networkidle", timeout=timeout)
        return True
    except Exception:
        # Fallback: wait fixed duration
        page.wait_for_timeout(3000)
        return False
```

---

## Pattern 4: Error Classification

```python
class ExtractionError(Exception):
    """Base class for extraction errors."""

class RateLimitError(ExtractionError):
    """Instagram returned 429 or rate limit page."""

class PrivateProfileError(ExtractionError):
    """Profile is private, cannot extract without auth."""

class ProfileNotFoundError(ExtractionError):
    """Profile does not exist (404)."""

def classify_page_error(page) -> ExtractionError | None:
    """Detect and classify Instagram error pages."""
    url = page.url
    title = page.title()
    
    if "429" in title or "rate" in title.lower():
        return RateLimitError("Rate limited by Instagram")
    if "Page Not Found" in title or "404" in title:
        return ProfileNotFoundError("Profile not found")
    if page.query_selector("text=This Account is Private"):
        return PrivateProfileError("Private profile")
    return None
```

---

## Pattern 5: Count Parsing

```python
import re

def parse_instagram_count(value: str | int | None) -> int | None:
    """Parse Instagram count strings like '1.2k', '3.4M', '5,678'.
    
    Args:
        value: Raw count value from Instagram
        
    Returns:
        Integer count, or None if unparseable.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value
    
    value = str(value).strip().replace(",", "")
    
    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
    
    match = re.match(r"^([\d.]+)\s*([kmb])?$", value.lower())
    if not match:
        return None
    
    number = float(match.group(1))
    suffix = match.group(2)
    
    if suffix:
        number *= multipliers[suffix]
    
    return int(number)
```

---

## Pattern 6: Hashtag Extraction

```python
def extract_hashtags(caption: str | None) -> list[str]:
    """Extract hashtags from a post caption.
    
    Args:
        caption: Post caption text
        
    Returns:
        List of hashtags (without # prefix, lowercase)
    """
    if not caption:
        return []
    
    hashtags = re.findall(r"#(\w+)", caption)
    return [tag.lower() for tag in hashtags]
```

---

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Instagram changes DOM selectors | Use `page.evaluate()` JSON extraction as primary |
| Bot detection triggers | Use human-like delays (2-4 seconds), realistic viewport |
| Browser resource leak | Always `browser.close()` in `finally` block |
| Timeout on slow pages | Set `timeout=30000` on `goto()`, use `wait_for_load_state` |
| Private profile confusion | Check page content before extraction, classify errors |
| Memory buildup | Create new browser context per extraction, not per run |

---

## Compliance Checklist

- [ ] Rate limiter called before every extraction
- [ ] Audit log entry created for every attempt
- [ ] PII stripped before any storage operation
- [ ] No authentication bypass attempted
- [ ] Browser fully closed in finally block
- [ ] Extraction limited to public data only

---

**End of Web Scraper Skill**
