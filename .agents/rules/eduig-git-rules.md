# EduIG-Pipeline Git Commit Rules
# File: .agents/rules/eduig-git-rules.md
# Enforcement: commitlint pre-commit hook

## Commit Message Format
<type>(<scope>): <description> [#<issue-number>]

## Types
- feat:     New feature or capability
- fix:      Bug fix
- docs:     Documentation only changes
- test:     Adding or updating tests
- refactor: Code change that neither fixes bug nor adds feature
- perf:     Performance improvement
- chore:    Build process or auxiliary tool changes
- style:    Formatting, missing semicolons, etc (no logic change)

## Scope (use module name)
- scaffold, config, logger, browser_worker, api_worker
- rate_limiter, router, parser, normalizer, storage
- compliance, schemas, run, tests, docs, notebooks

## Rules
- Description must be lowercase, imperative mood, no period at end
- Issue number is REQUIRED for all non-trivial commits
- Maximum 72 characters for subject line
- Use body for explaining WHY, not WHAT (what is in the diff)

## Valid Examples
feat(rate_limiter): add circuit breaker with configurable threshold [#6]
fix(parser): handle missing bio field gracefully [#15]
test(storage): add WAL mode concurrency integration tests [#11]
docs(readme): add installation and configuration sections [#19]
refactor(normalizer): extract pii stripping into separate class [#10]
chore(scaffold): initialize project structure and gitignore [#1]
style(src): apply black formatting across all modules [#20]

## Invalid Examples (DO NOT USE)
WIP
fix stuff
update
done
working now
