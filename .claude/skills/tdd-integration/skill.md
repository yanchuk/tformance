---
name: tdd-integration
description: Enforce Test-Driven Development with strict Red-Green-Refactor cycle for Django. Auto-triggers when implementing new features or functionality. Trigger phrases include "implement", "add feature", "build", "create functionality", or any request to add new behavior. Does NOT trigger for bug fixes, documentation, or configuration changes.
---

# TDD Integration Testing (Django)

Enforce strict Test-Driven Development using the Red-Green-Refactor cycle with dedicated subagents.

## Pre-Flight Check

Before starting TDD, run existing tests to ensure a clean baseline:

```bash
make test
```

If tests fail, fix them before proceeding with new features.

## Mandatory Workflow

Every new feature MUST follow this strict 3-phase cycle. Do NOT skip phases.

### Phase 1: RED - Write Failing Test

🔴 RED PHASE: Delegating to tdd-test-writer...

Invoke the `tdd-test-writer` subagent with:
- Feature requirement from user request
- Expected behavior to test
- Target app name (e.g., `apps.integrations`, `apps.metrics`)

The subagent returns:
- Test file path (e.g., `apps/myapp/tests/test_feature.py`)
- Failure output confirming test fails
- Summary of what the test verifies

**Do NOT proceed to Green phase until test failure is confirmed.**

### Phase 2: GREEN - Make It Pass

🟢 GREEN PHASE: Delegating to tdd-implementer...

Invoke the `tdd-implementer` subagent with:
- Test file path from RED phase
- Feature requirement context

The subagent returns:
- Files modified (models, views, urls, etc.)
- Success output confirming test passes
- Implementation summary

**Do NOT proceed to Refactor phase until test passes.**

### Phase 3: REFACTOR - Improve

🔵 REFACTOR PHASE: Delegating to tdd-refactorer...

Invoke the `tdd-refactorer` subagent with:
- Test file path
- Implementation files from GREEN phase

The subagent returns either:
- Changes made + test success output, OR
- "No refactoring needed" with reasoning

**Cycle complete when refactor phase returns.**

## Test Commands

```bash
# Run all tests
make test

# Run specific test file
make test ARGS='apps.myapp.tests.test_feature'

# Run specific test class
make test ARGS='apps.myapp.tests.test_feature::TestClassName'

# Run specific test method
make test ARGS='apps.myapp.tests.test_feature::TestClassName::test_method'

# Keep database between runs (faster)
make test ARGS='apps.myapp.tests.test_feature --keepdb'
```

## Multiple Features

Complete the full cycle for EACH feature before starting the next:

```
Feature 1: 🔴 → 🟢 → 🔵 ✓
Feature 2: 🔴 → 🟢 → 🔵 ✓
Feature 3: 🔴 → 🟢 → 🔵 ✓
```

## Phase Violations

Never:
- Write implementation before the test
- Proceed to Green without seeing Red fail
- Skip Refactor evaluation
- Start a new feature before completing the current cycle
- Break existing tests

## Django-Specific Considerations

- Tests go in `apps/<app_name>/tests/` directory
- Use `django.test.TestCase` for database tests
- Use `django.test.Client` for view/API tests
- Models should extend `BaseModel` or `BaseTeamModel`
- Team-scoped tests need proper team context setup
