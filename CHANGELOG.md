# Changelog
All notable changes to this project will be documented in this file.

## [1.0-authenticated] - 2026-06-02

### Added (Task A - Session Manager Foundation)
- `src/auth/session_manager.py` - Core authenticated session management
- `src/auth/credential_store.py` - Fernet-encrypted session persistence
- `src/auth/two_fa_handler.py` - TOTP/backup/stdin 2FA handling
- `src/auth/exceptions.py` - Authentication error hierarchy
- `scripts/generate_encryption_key.py` - Encryption key generator

### Added (Task B - Anti-Detection Browser)
- `src/auth/stealth_browser.py` - Stealth Chromium with anti-detection
- `src/auth/fingerprint_manager.py` - Consistent fingerprint per session
- `src/auth/behavior_mimicry.py` - Human-like mouse/typing/scroll
- `scripts/test_stealth.py` - Bot detection verification (bot.sannysoft.com)

### Added (Task C - Login Flow)
- Real Instagram login with human-like behavior
- Post-login prompt dismissal ("Save login info", "Turn on notifications")
- Suspicious login handling ("This was me")
- `scripts/test_login.py` - Manual login verification

### Added (Task D - Authenticated Extraction)
- `src/auth/authenticated_worker.py` - Exact count extraction via i.instagram.com API
- GraphQL pagination fallback
- Exact engagement rate calculation
- `scripts/test_authenticated_extraction.py` - Manual extraction verification

### Added (Task E - Integration & Testing)
- `tests/integration/test_full_authenticated_pipeline.py` - End-to-end integration
- `tests/integration/test_fallback_pipeline.py` - Fallback integration
- `scripts/generate_compliance_report.py` - Audit report generator
- Makefile with test, lint, secrets, integration, report targets

### Skills Used
- web-scraper - Anti-detection patterns, session management
- api-patterns - Authentication flows, GraphQL design
- workflow-automation - Task sequencing, error recovery
- bash-scripting - Setup scripts, Makefile targets

### Modified
- `src/router.py` - Added route_authenticated()
- `src/schemas.py` - Added AuthenticatedProfileSchema
- `src/parser.py` - Added parse_authenticated_profile()
- `src/normalizer.py` - Added normalize_authenticated_data()
- `src/storage.py` - Added exact field migration
- `src/run.py` - Added --authenticated and --test-login flags
- `README.md` - Authentication setup documentation
- `CONTRIBUTING.md` - CI warnings for manual tests
