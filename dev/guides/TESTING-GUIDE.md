# Testing Guide

> Back to [CLAUDE.md](../../CLAUDE.md)

## Test-Driven Development (TDD)

**This project follows strict TDD practices. All new features MUST use Red-Green-Refactor cycle.**

### Before Starting Any Implementation

1. **Run existing tests first**: `make test` to ensure passing state
2. **Identify existing tests**: Check `apps/<app>/tests/` for related files
3. **Never break existing tests**: Fix failures before proceeding

### TDD Workflow

#### RED Phase - Write Failing Test First
- Write a test that describes expected behavior
- Run test and confirm it **fails** (proves test is valid)
- Do NOT write implementation code yet

#### GREEN Phase - Make It Pass
- Write **minimum** code needed to pass
- No extra features, no "nice to haves"
- Run test and confirm it **passes**

#### REFACTOR Phase - Improve
- Clean up while keeping tests green
- Extract reusable code, improve naming, remove duplication
- Run tests after each change

### TDD Skill Activation

Project has Claude Code skills configured to enforce TDD:
1. `tdd-test-writer` agent for RED phase
2. `tdd-implementer` agent for GREEN phase
3. `tdd-refactorer` agent for REFACTOR phase

**Trigger phrases**: "implement", "add feature", "build", "create functionality"
**Does NOT trigger**: bug fixes, documentation, configuration changes

## Test File Conventions

Pattern: `apps/<app_name>/tests/test_<feature>.py`

## Test Structure (Django TestCase with Factories)

```python
from django.test import TestCase
from apps.metrics.factories import TeamMemberFactory, PullRequestFactory
from apps.teams.factories import TeamFactory


class TestFeatureName(TestCase):
    """Tests for <feature description>."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_describes_expected_behavior(self):
        """Test that <specific behavior> works correctly."""
        # Arrange - use factories for test data
        pr = PullRequestFactory(team=self.team, author=self.member)

        # Act - perform the action
        # Assert - verify the outcome
        self.assertEqual(pr.author, self.member)
```

## Factory Guidelines

- **Always use factories** for test data instead of manual model creation
- Factories located in `apps/<app>/factories.py`
- `Factory.build()` for unit tests (doesn't save to DB)
- `Factory.create()` or `Factory()` for integration tests (saves to DB)
- `Factory.create_batch(n)` to create multiple instances
- Override attributes: `TeamMemberFactory(role="lead", display_name="John")`

**Use `factory.Sequence` for unique fields:**
```python
email = factory.Sequence(lambda n: f"user{n}@example.com")
github_id = factory.Sequence(lambda n: str(10000 + n))
```

### Available Factories

**`apps/metrics/factories.py`:**
- `TeamFactory`, `TeamMemberFactory`
- `PullRequestFactory`, `PRReviewFactory`, `CommitFactory`
- `JiraIssueFactory`, `AIUsageDailyFactory`
- `PRSurveyFactory`, `PRSurveyReviewFactory`
- `WeeklyMetricsFactory`

**Other locations:**
- `apps/feedback/factories.py`
- `apps/integrations/factories.py`
- `apps/notes/factories.py`

## E2E Testing (Playwright)

**Requires dev server running.**

Key test suites in `tests/e2e/`:
- `smoke.spec.ts` - Basic page loads, health checks
- `auth.spec.ts` - Login, logout, access control
- `dashboard.spec.ts` - CTO dashboard, navigation
- `integrations.spec.ts` - Integration status pages
- `onboarding.spec.ts` - Onboarding flow
- `pr-list.spec.ts` - PR list features
- `insights.spec.ts` - AI insights
- `htmx-*.spec.ts` - HTMX integration tests
- `accessibility.spec.ts` - A11y checks

**Test Credentials:** `admin@example.com` / `admin123`

**When to Run E2E:**
- After changing views, templates, URL patterns
- After modifying authentication/access control
- Before major releases
- When debugging user-reported issues

## Visual Verification with Playwright MCP

When implementing UI changes:
1. Make code changes
2. Use `mcp__playwright__browser_navigate` to load affected page
3. Use `mcp__playwright__browser_snapshot` to capture accessibility state
4. Use `mcp__playwright__browser_take_screenshot` for visual confirmation
5. Verify changes match requirements

## Command Reference

See [COMMANDS-REFERENCE.md](./COMMANDS-REFERENCE.md) for full testing commands.
