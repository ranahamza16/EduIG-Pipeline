# Makefile — EduIG-Pipeline common commands
# Usage: make <target>
# Requires: Python 3.10+, virtual environment at ./venv

.PHONY: install health-check test test-unit test-integration lint format \
        format-check typecheck run dry-run clean help secrets integration report all

# Default target
help:
	@echo "EduIG-Pipeline — Available Commands"
	@echo "===================================="
	@echo "  make install          Set up virtual env and install all dependencies"
	@echo "  make health-check     Verify all imports and Python version"
	@echo "  make test             Run unit tests with coverage (>=80%)"
	@echo "  make integration      Run integration tests only"
	@echo "  make lint             Run mypy, black, isort, and flake8"
	@echo "  make secrets          Run git-secrets scan"
	@echo "  make report           Generate compliance report"
	@echo "  make all              Run lint, test, integration, secrets, and report"
	@echo "  make run              Run the pipeline (reads config/targets.csv)"
	@echo "  make dry-run          Validate config without scraping"
	@echo "  make clean            Remove caches and build artifacts"

install:
	bash scripts/setup.sh

health-check:
	python scripts/health_check.py

test:
	pytest tests/ -v --cov=src --cov-fail-under=80 --ignore=tests/integration/

lint:
	mypy src/ --strict && black src/ --check && isort src/ --check-only && flake8 src/ --max-line-length=100 --extend-ignore=E501,E402,W293,F401,F541,E203

secrets:
	git-secrets --scan

integration:
	pytest tests/integration/ -v

report:
	@echo "Generating compliance report..."
	python scripts/generate_compliance_report.py

dashboard:
	@echo "Starting EduIG Dashboard..."
	PYTHONPATH=. python src/dashboard/app.py

dashboard-test:
	@echo "Running dashboard tests..."
	pytest tests/test_dashboard_api.py tests/test_dashboard_pwa.py tests/test_dashboard_styling.py -v --cov=src.dashboard --cov-fail-under=80

dashboard-lint:
	@echo "Linting dashboard..."
	mypy src/dashboard/ --strict
	black src/dashboard/ --check
	isort src/dashboard/ --check-only
	flake8 src/dashboard/ --max-line-length=100

all: lint test integration secrets report dashboard-test
	@echo "Full pipeline complete."

format:
	black src/ tests/
	isort src/ tests/

format-check:
	black --check src/ tests/
	isort --check-only src/ tests/

typecheck:
	mypy src/ --strict

run:
	python run.py --config config/settings.yaml

dry-run:
	python run.py --dry-run

clean:
	@echo "Cleaning caches..."
	@find . -type d -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -not -path "./venv/*" -delete 2>/dev/null || true
	@find . -name ".pytest_cache" -not -path "./venv/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".mypy_cache" -not -path "./venv/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".coverage" -delete 2>/dev/null || true
	@echo "Clean complete."
