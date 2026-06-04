# Contributing to EduIG-Pipeline

Thank you for contributing! This document explains how to work on EduIG-Pipeline effectively as a team.

---

## Table of Contents
- [Development Setup](#development-setup)
- [Branch Strategy](#branch-strategy)
- [Commit Message Format](#commit-message-format)
- [Pull Request Process](#pull-request-process)
- [Code Review Checklist](#code-review-checklist)
- [Quality Standards](#quality-standards)

---

## Development Setup

```bash
# Windows
.\scripts\setup.ps1

# Linux / Mac
bash scripts/setup.sh

# Verify everything works
python scripts/health_check.py

# Run tests
pytest tests/ -v --cov=src --cov-fail-under=80

> [!WARNING]
> **Never run `scripts/test_login.py` in CI.** Manual test only, requires real credentials.

# Type check
mypy src/ --strict

# Format code
black src/ tests/
isort src/ tests/
```

---

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `master` | Stable, tested code only. Direct pushes forbidden. |
| `dev-a/feature-name` | Developer A's feature branches |
| `dev-b/feature-name` | Developer B's feature branches |

### Branch Naming Examples
```
dev-a/task-3-config-system
dev-b/task-6-rate-limiter
dev-a/fix-parser-missing-bio
dev-b/test-storage-wal-mode
```

### Workflow
```
1. Pull latest master:   git pull origin master
2. Create branch:        git checkout -b dev-a/task-N-description
3. Do your work
4. Run full checks:      make test && make lint && make typecheck
5. Commit:               git commit -m "feat(module): description [#N]"
6. Push:                 git push origin dev-a/task-N-description
7. Open PR → request review
8. Merge after approval
```

---

## Commit Message Format

Format: `<type>(<scope>): <description> [#<issue>]`

### Types
| Type | Use For |
|------|---------|
| `feat` | New feature or module |
| `fix` | Bug fix |
| `test` | Adding or fixing tests |
| `docs` | Documentation only |
| `refactor` | Code restructure, no feature change |
| `perf` | Performance improvement |
| `chore` | Build, tooling, dependencies |
| `style` | Formatting only (black, isort) |

### Scopes (use module names)
`scaffold`, `config`, `logger`, `browser_worker`, `api_worker`, `rate_limiter`, `router`, `parser`, `normalizer`, `storage`, `compliance`, `schemas`, `run`, `tests`, `docs`, `notebooks`

### Valid Examples
```
feat(rate_limiter): add circuit breaker with configurable threshold [#6]
fix(parser): handle missing bio field gracefully [#15]
test(storage): add WAL mode concurrency integration tests [#11]
docs(readme): add installation and configuration sections [#19]
refactor(normalizer): extract pii stripping into separate class [#10]
chore(deps): pin playwright to 1.41.0 [#2]
style(src): apply black formatting across all modules [#20]
```

### Invalid (will be rejected)
```
WIP
fix stuff
update
done
working now
```

---

## Pull Request Process

### Before Opening a PR
- [ ] All tests pass: `pytest --cov=src --cov-fail-under=80`
- [ ] mypy strict passes: `mypy src/ --strict`
- [ ] Code formatted: `black --check src/ && isort --check-only src/`
- [ ] No print statements in src/: `grep -rn "print(" src/` (empty)
- [ ] No secrets/tokens in code
- [ ] Walkthrough written or updated

### PR Description Template
```markdown
## What This PR Does
<!-- Brief description -->

## Task Reference
Closes #<task-number>

## Changes
- [ ] `src/<module>.py` — what changed
- [ ] `tests/test_<module>.py` — what was tested

## Test Results
<!-- Paste pytest output here -->

## Coverage
<!-- Paste coverage summary here -->

## mypy
<!-- Paste mypy output here (should say: "Success: no issues found") -->
```

---

## Code Review Checklist

Reviewers must verify:

### Correctness
- [ ] Logic is correct and handles edge cases
- [ ] Error handling is present on all external calls
- [ ] No infinite loops (all loops have max iteration guards)

### Compliance (AI_RULES.md)
- [ ] Python 3.10+ syntax (`str | None`, not `Optional[str]`)
- [ ] Pydantic v2 models for all cross-module data
- [ ] Playwright used (not Selenium)
- [ ] httpx used (not requests)
- [ ] structlog used (no print statements)
- [ ] Rate limiter called before any Instagram request
- [ ] PII stripped before any storage operation
- [ ] No credentials or tokens in code

### Quality
- [ ] All public methods have Google-style docstrings
- [ ] Type hints on all function signatures
- [ ] Tests cover ≥80% of new code
- [ ] mypy strict passes
- [ ] black + isort formatting applied

---

## Quality Standards

| Standard | Tool | Threshold |
|----------|------|-----------|
| Test coverage | pytest-cov | ≥80% |
| Type safety | mypy --strict | 0 errors |
| Formatting | black | 0 diffs |
| Import order | isort | 0 diffs |
| Linting | flake8 | 0 violations |
| Print statements | grep | 0 matches in src/ |

All standards must pass before any merge into `master`.

---

*Questions? Check `docs/AI_RULES.md` first, then ask your team member.*
