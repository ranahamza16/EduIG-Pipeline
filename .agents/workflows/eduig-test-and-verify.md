# Title: EduIG Test & Verify Workflow
# Description: Run full test suite and verify compliance after every 4-5 tasks
# Usage: Run at each phase gate and before marking a phase complete

Step 1:  Run full test suite with coverage:
         pytest --cov=src --cov-fail-under=80 --cov-report=term-missing -v

Step 2:  Run mypy strict type checking:
         mypy src/ --strict

Step 3:  Run formatting checks (do NOT auto-fix here, just check):
         black --check src/ && isort --check-only src/

Step 4:  Run linter:
         flake8 src/ --max-line-length=100

Step 5:  Check for forbidden print() statements in src/:
         grep -rn "print(" src/ (output must be EMPTY)

Step 6:  Check for hardcoded credentials/tokens:
         grep -rEn "(password|token|secret|api_key)\s*=\s*['\"][^'\"]{4,}" src/

Step 7:  Run pipeline dry-run to verify wiring:
         python run.py --dry-run

Step 8:  Verify audit log entries are being written:
         Check that data/logs/audit.log has entries after dry-run

Step 9:  Verify raw data retention policy:
         Check that compliance module correctly identifies files for deletion

Step 10: Generate compliance summary:
         python -c "from src.compliance import AuditGenerator; print(AuditGenerator().generate_report('test'))"

Step 11: Report results:
         - All checks PASS → proceed to next phase
         - Any FAIL → fix before proceeding, do NOT lower standards
