#!/usr/bin/env python3
"""Standalone script to visually test StealthBrowser against bot.sannysoft.com."""

import asyncio
import os
import sys

# Ensure src is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.auth.fingerprint_manager import FingerprintManager
from src.auth.stealth_browser import StealthBrowser

async def main():
    print("Generating fingerprint...")
    fm = FingerprintManager("bot_tester")
    fingerprint = fm.generate()
    
    print("Launching stealth browser...")
    browser = StealthBrowser(fingerprint)
    
    # Launch headful if you want to watch it, but headless is the true test
    await browser.launch(headless=True)
    
    print("Navigating to bot.sannysoft.com...")
    page = await browser.new_page()
    await page.goto("https://bot.sannysoft.com/", timeout=60000)
    
    # Wait for the test to complete rendering
    await asyncio.sleep(5)
    
    screenshot_path = "sannysoft_result.png"
    await page.screenshot(path=screenshot_path, full_page=True)
    
    print(f"Done! Screenshot saved to {screenshot_path}")
    print("Open the image and verify that all rows are GREEN (no red flags).")
    
    await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
