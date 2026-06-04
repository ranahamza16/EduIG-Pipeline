#!/usr/bin/env python3
"""
WARNING: This script uses REAL Instagram credentials from .env
Run at your own risk. Account ban/lock possible.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.auth.session_manager import AuthenticatedSessionManager
from src.logger import get_logger

logger = get_logger()

async def main() -> int:
    print("=" * 60)
    print("WARNING: This script uses REAL Instagram credentials from .env")
    print("Run at your own risk. Account ban/lock possible.")
    print("=" * 60)
    print()

    load_dotenv()
    
    manager = AuthenticatedSessionManager(dict(os.environ))
    os.makedirs("data/artifacts", exist_ok=True)
    exit_code = 1
    
    try:
        print("[*] Initializing session manager...")
        await manager.initialize()
        
        print("[*] Attempting login...")
        login_success = await manager.login()
        
        if not login_success:
            print("[-] Login flow returned False.")
            return 1
            
        print("[*] Verifying session...")
        is_valid = await manager.verify_session()
        
        if is_valid:
            print("\n[+] Login successful! Session established.")
            if manager.stealth_browser and manager.stealth_browser.context:
                pages = manager.stealth_browser.context.pages
                if pages:
                    await pages[0].screenshot(path="data/artifacts/login_result.png")
                    print("[+] Screenshot saved to data/artifacts/login_result.png")
            exit_code = 0
        else:
            print("\n[-] Login verification failed.")
            print("[-] Login failed. Check logs for details.")
            if manager.stealth_browser and manager.stealth_browser.context:
                pages = manager.stealth_browser.context.pages
                if pages:
                    await pages[0].screenshot(path="data/artifacts/login_failed.png")
                    print("[-] Screenshot saved to data/artifacts/login_failed.png")
            exit_code = 1
            
    except Exception as e:
        print(f"\n[-] Login failed with error: {str(e)}")
        print("[-] Login failed. Check logs for details.")
        if manager.stealth_browser and manager.stealth_browser.context:
            try:
                pages = manager.stealth_browser.context.pages
                if pages:
                    await pages[0].screenshot(path="data/artifacts/login_failed.png")
                    print("[-] Screenshot saved to data/artifacts/login_failed.png")
            except Exception as ss_err:
                print(f"[-] Could not take failure screenshot: {ss_err}")
        exit_code = 1
        
    finally:
        print("[*] Closing session manager...")
        await manager.close()
        
    return exit_code

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
