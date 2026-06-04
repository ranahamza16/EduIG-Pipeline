# Title: EduIG Build Phase Workflow
# Description: Execute one phase of the EduIG-Pipeline implementation
# Usage: Follow these steps for EVERY implementation task

Step 1:  Read PLAN.md → identify the CURRENT TASK number and requirements.
Step 2:  Read ARCHITECTURE.md → understand the module's design and interfaces.
Step 3:  Read AI_RULES.md → verify all compliance constraints for this task.
Step 4:  Read the matching prompt section in PROMPT_FOR_ANTIGRAVITY.md.
Step 5:  Read relevant skill files:
         - web-scraper skill for any Playwright patterns
         - api-patterns skill for any httpx/HTTP patterns
         - bash-scripting skill for any setup scripts
         - workflow-automation skill for orchestration patterns
Step 6:  Create implementation_plan.md artifact detailing:
         - Files to create/modify
         - Classes and methods to implement
         - Tests to write
         - Verification commands
Step 7:  PAUSE — wait for human approval of implementation plan.
Step 8:  Write source code following ALL rules in .agents/rules/eduig-code-style.md.
Step 9:  Write unit tests (minimum 80% coverage for the new module).
Step 10: Run tests: pytest tests/test_<module>.py -v --cov=src.<module> --cov-fail-under=80
Step 11: Fix ANY test failures before proceeding. Do not skip.
Step 12: Run mypy: mypy src/<module>.py --strict
Step 13: Fix ALL type errors. No `# type: ignore` without documented reason.
Step 14: Run formatters: black src/<module>.py && isort src/<module>.py
Step 15: Update task.md — mark current task as [x] complete.
Step 16: Create walkthrough.md artifact summarizing:
         - What was built and why
         - Key design decisions
         - How to verify it works
         - What the next task is
Step 17: PAUSE — wait for human approval before starting next task.
