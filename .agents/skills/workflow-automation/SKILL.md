# Workflow Automation Skill
## Agent Workflow Orchestration for EduIG-Pipeline

---

## Overview

This skill defines how to structure, execute, and verify agent-driven development workflows for the EduIG-Pipeline project. It governs how Antigravity agent sessions are organized, how tasks are handed off, and how quality is enforced at each step.

---

## Core Principles

1. **One Task Per Session** — Never attempt multiple tasks in one agent session
2. **Plan Before Code** — Always enter Plan Mode first; no coding without an approved plan
3. **Test Before Proceeding** — Tests must pass before moving to next task
4. **Artifact After Every Task** — Every completed task produces a walkthrough artifact
5. **Human Approval Required** — Agent pauses after every task for review

---

## Workflow 1: EduIG Build Phase

Use this workflow for **every implementation task**.

```
Step 1: Read PLAN.md → identify CURRENT TASK and its requirements
Step 2: Read ARCHITECTURE.md → understand module design and interfaces  
Step 3: Read AI_RULES.md → verify compliance constraints for this task
Step 4: Read the matching prompt from PROMPT_FOR_ANTIGRAVITY.md
Step 5: Create implementation plan artifact (implementation_plan.md)
         - What files will be created/modified
         - What tests will be written
         - What dependencies are needed
         - What the verification command is
Step 6: PAUSE → wait for human approval of the plan
Step 7: Write the code following all AI_RULES
Step 8: Write unit tests (≥80% coverage requirement)
Step 9: Run tests → fix any failures before proceeding
Step 10: Run mypy → fix any type errors
Step 11: Run black + isort → ensure formatting
Step 12: Update task.md → mark task as [x] complete
Step 13: Create walkthrough artifact summarizing what was built
Step 14: PAUSE → wait for human approval before next task
```

---

## Workflow 2: EduIG Test & Verify

Use this workflow **after every 4-5 tasks** and at each phase gate.

```
Step 1: Run full test suite:
        pytest --cov=src --cov-fail-under=80 --cov-report=term-missing

Step 2: Run type checking:
        mypy src/ --strict

Step 3: Run formatting check:
        black --check src/ && isort --check-only src/

Step 4: Run linting:
        flake8 src/ --max-line-length=100

Step 5: Check for print statements (forbidden in src/):
        grep -r "print(" src/ (should return empty)

Step 6: Check for hardcoded credentials:
        grep -rE "(password|token|secret|key)\s*=\s*['\"][^'\"]{8,}" src/

Step 7: Run integration test on sample data:
        python run.py --dry-run

Step 8: Verify audit log entries are written

Step 9: Verify raw data retention policy is enforced

Step 10: Generate compliance summary report
```

---

## Communication Protocol

| Situation | Agent Action |
|-----------|-------------|
| Task complete | Create walkthrough artifact → pause for review |
| Rule violation found | STOP → report rule number + violation → suggest fix |
| Unclear requirement | Ask ONE clarifying question → wait for answer |
| Test failure | Fix immediately → do not skip → do not proceed |
| External dependency issue | Document workaround → suggest alternative |
| Compliance concern | Flag with severity → suggest mitigation |
| mypy error | Fix before proceeding → type safety is non-negotiable |
| Coverage below 80% | Add tests → do not lower the threshold |

---

## Task Handoff Template

After completing each task, produce this summary:

```markdown
## Task [N] Complete: [Task Name]

### What Was Built
- [File 1]: [brief description]
- [File 2]: [brief description]

### Tests
- Tests written: [count]
- Coverage: [X]%
- All passing: ✓ / ✗

### Quality Checks
- [ ] mypy strict: PASS / FAIL
- [ ] black formatting: PASS / FAIL  
- [ ] isort: PASS / FAIL
- [ ] flake8: PASS / FAIL
- [ ] No print() statements: PASS / FAIL
- [ ] No hardcoded credentials: PASS / FAIL

### Verification Command
```bash
[exact command to verify this task works]
```

### Next Task
Task [N+1]: [name] — [brief description of what's next]

### Human Action Required
- [ ] Run verification command
- [ ] Review test output
- [ ] Approve to proceed
```

---

## Phase Gate Checklist

### Gate 1: Foundation → Core Pipeline
```
- [ ] python -c "from src.config_loader import load_config; print(load_config())"
- [ ] python -c "from src.browser_worker import BrowserWorker; print('OK')"
- [ ] python -c "from src.logger import get_logger; get_logger().info('test')"
- [ ] pytest tests/ -v (all 5 task tests passing)
- [ ] Coverage ≥ 80%
```

### Gate 2: Core Pipeline → Compliance
```
- [ ] python run.py --dry-run (no errors)
- [ ] Full pipeline on 3 test targets
- [ ] Data present in SQLite: sqlite3 data/eduig.db "SELECT COUNT(*) FROM profiles;"
- [ ] CSV export generated
- [ ] Audit log has entries
- [ ] Coverage ≥ 80% across all modules
```

### Gate 3: Compliance → Advanced
```
- [ ] Usernames hashed: sqlite3 data/eduig.db "SELECT username_hash FROM profiles LIMIT 1;"
- [ ] No PII in bios: grep -i "@" (should be empty from DB)
- [ ] Raw data deletion works: verify files deleted after retention period
- [ ] All integration tests pass
```

### Gate 4: Advanced → Polish
```
- [ ] Post extraction returns engagement_rate
- [ ] Notebooks execute without errors
- [ ] API worker returns data with valid token (optional)
```

### Gate 5: Polish → Release
```
- [ ] pytest --cov=src --cov-fail-under=80 PASSES
- [ ] mypy src/ --strict PASSES
- [ ] black --check src/ PASSES
- [ ] README is complete and readable
- [ ] git tag v1.0 created
```

---

## Error Recovery Procedures

### If Agent Gets Stuck Mid-Task
1. Cancel current session
2. Note exactly what was completed
3. Start new session with prompt: "Continue Task [N]. The following is already done: [list]. Start from [specific step]."
4. Never re-do already-completed work

### If Tests Fail After "Done"
1. Paste EXACT error output into new session
2. Prompt: "Fix this test failure ONLY. Do not change unrelated code. Here is the error: [paste]"
3. Verify fix does not break other tests
4. Re-run full suite before marking complete

### If mypy Fails
1. Paste exact mypy error
2. Prompt: "Fix this mypy strict error. Use Python 3.10+ union syntax (str | None, not Optional[str])."
3. Never disable mypy checks with `# type: ignore` unless documented

### If Coverage < 80%
1. List uncovered lines from `--cov-report=term-missing`
2. Prompt: "Add tests to cover these uncovered lines: [paste]. Do not change source code."

---

## Artifact Naming Convention

| Artifact Type | Naming Pattern | Example |
|--------------|----------------|---------|
| Implementation Plan | `implementation_plan.md` | Updated for each task |
| Task Tracker | `task.md` | Updated throughout |
| Walkthrough | `walkthrough.md` | Updated after each task |
| Test Reports | `test_report_task_{N}.md` | Per task |
| Compliance Reports | `compliance_report_{date}.md` | Per run |

---

## Session Startup Checklist

Before every agent session:
```
1. Read PLAN.md → identify current task
2. Check task.md → verify previous task is marked [x]
3. Run: git status (should be clean)
4. Run: pytest tests/ (previous tests still passing)
5. Activate venv: source venv/bin/activate (Linux) or venv\Scripts\activate (Windows)
6. Paste task prompt into Plan Mode
```

---

**End of Workflow Automation Skill**
