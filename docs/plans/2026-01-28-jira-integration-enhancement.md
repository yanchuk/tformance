# Jira Integration Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance Jira integration to provide full data flow from Jira tickets through PR enrichment to LLM insights and dashboards.

**Architecture:** Extend existing Jira sync to capture changelog data (time-in-status, status transitions), inject Jira context into LLM prompts for PR analysis and insights, and enrich dashboard metrics with story points and linkage rates. Keep Jira pipeline independent from GitHub to avoid failure coupling.

**Tech Stack:** Django 5.2, PostgreSQL (JSONField with GIN index), Celery, Jinja2 templates, HTMX, Waffle feature flags

**Branch:** `feature/jira-integration-enhancement` (work in dedicated git worktree)

---

## Phase 1: Foundation (Models + Migrations)

### Task 1: Add time_in_status and status_transitions to JiraIssue model

**Files:**
- Modify: `apps/metrics/models/jira.py`
- Create: `apps/metrics/migrations/XXXX_jira_time_in_status.py` (auto-generated)
- Test: `apps/metrics/tests/models/test_jira_issue.py`

**Step 1: Write the failing test**

Add to `apps/metrics/tests/models/test_jira_issue.py`:

```python
from decimal import Decimal
from django.test import TestCase
from apps.metrics.factories import JiraIssueFactory, TeamFactory


class JiraIssueTimeInStatusTest(TestCase):
    """Tests for time_in_status and status_transitions fields."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    def test_time_in_status_default_empty_dict(self):
        """time_in_status defaults to empty dict."""
        issue = JiraIssueFactory(team=self.team)
        self.assertEqual(issue.time_in_status, {})

    def test_time_in_status_stores_hours_per_status(self):
        """time_in_status stores hours spent in each status."""
        issue = JiraIssueFactory(
            team=self.team,
            time_in_status={"In Progress": 8.5, "Code Review": 12.0}
        )
        self.assertEqual(issue.time_in_status["In Progress"], 8.5)
        self.assertEqual(issue.time_in_status["Code Review"], 12.0)

    def test_status_transitions_default_zero(self):
        """status_transitions defaults to 0."""
        issue = JiraIssueFactory(team=self.team)
        self.assertEqual(issue.status_transitions, 0)

    def test_status_transitions_counts_changes(self):
        """status_transitions counts number of status changes."""
        issue = JiraIssueFactory(team=self.team, status_transitions=5)
        self.assertEqual(issue.status_transitions, 5)
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest apps/metrics/tests/models/test_jira_issue.py::JiraIssueTimeInStatusTest -v
```

Expected: FAIL with `AttributeError: 'JiraIssue' object has no attribute 'time_in_status'`

**Step 3: Add fields to JiraIssue model**

Edit `apps/metrics/models/jira.py`, add after `cycle_time_hours` field (around line 126):

```python
    # Time-in-status tracking (from Jira changelog)
    time_in_status = models.JSONField(
        default=dict,
        verbose_name="Time in Status",
        help_text="Hours spent in each status, e.g., {'In Progress': 12.5, 'Code Review': 8.0}",
    )
    status_transitions = models.IntegerField(
        default=0,
        verbose_name="Status Transitions",
        help_text="Number of status changes (rework indicator)",
    )
```

**Step 4: Create migration**

```bash
.venv/bin/python manage.py makemigrations metrics --name jira_time_in_status
```

Expected: Migration file created

**Step 5: Run migration**

```bash
.venv/bin/python manage.py migrate metrics
```

Expected: Migration applied successfully

**Step 6: Run test to verify it passes**

```bash
.venv/bin/pytest apps/metrics/tests/models/test_jira_issue.py::JiraIssueTimeInStatusTest -v
```

Expected: All 4 tests PASS

**Step 7: Commit**

```bash
git add apps/metrics/models/jira.py apps/metrics/migrations/*jira_time_in_status* apps/metrics/tests/models/test_jira_issue.py
git commit -m "feat(jira): add time_in_status and status_transitions fields to JiraIssue

- time_in_status: JSONField storing hours per status
- status_transitions: IntegerField counting status changes (rework indicator)
- Used for bottleneck analysis and rework detection"
```

---

### Task 2: Add GIN index for time_in_status JSONField

**Files:**
- Modify: `apps/metrics/models/jira.py`
- Create: Migration (auto-generated)

**Step 1: Write test for index existence**

Add to `apps/metrics/tests/models/test_jira_issue.py`:

```python
def test_time_in_status_has_gin_index(self):
    """time_in_status field should have GIN index for efficient queries."""
    from apps.metrics.models import JiraIssue

    index_names = [idx.name for idx in JiraIssue._meta.indexes]
    self.assertIn("jira_time_in_status_gin_idx", index_names)
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest apps/metrics/tests/models/test_jira_issue.py::JiraIssueTimeInStatusTest::test_time_in_status_has_gin_index -v
```

Expected: FAIL with `AssertionError`

**Step 3: Add GIN index to model Meta**

Edit `apps/metrics/models/jira.py`, in the `Meta` class `indexes` list, add:

```python
from django.contrib.postgres.indexes import GinIndex

class Meta:
    # ... existing ...
    indexes = [
        models.Index(fields=["jira_key"], name="jira_issue_key_idx"),
        models.Index(fields=["resolved_at"], name="jira_resolved_at_idx"),
        models.Index(fields=["assignee", "status"], name="jira_assignee_status_idx"),
        models.Index(fields=["sprint_id"], name="jira_sprint_idx"),
        # NEW: GIN index for time_in_status JSON queries
        GinIndex(fields=["time_in_status"], name="jira_time_in_status_gin_idx"),
    ]
```

**Step 4: Create and run migration**

```bash
.venv/bin/python manage.py makemigrations metrics --name jira_time_in_status_gin_index
.venv/bin/python manage.py migrate metrics
```

**Step 5: Run test to verify it passes**

```bash
.venv/bin/pytest apps/metrics/tests/models/test_jira_issue.py::JiraIssueTimeInStatusTest::test_time_in_status_has_gin_index -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add apps/metrics/models/jira.py apps/metrics/migrations/*gin_index*
git commit -m "perf(jira): add GIN index for time_in_status JSONField

Enables efficient queries for bottleneck analysis on JSON data"
```

---

### Task 3: Add story_points_field to JiraIntegration model

**Files:**
- Modify: `apps/integrations/models/jira.py`
- Create: Migration (auto-generated)
- Test: `apps/integrations/tests/test_models.py`

**Step 1: Write the failing test**

Add to `apps/integrations/tests/test_models.py`:

```python
from django.test import TestCase
from apps.integrations.factories import JiraIntegrationFactory
from apps.metrics.factories import TeamFactory


class JiraIntegrationStoryPointsFieldTest(TestCase):
    """Tests for story_points_field configuration."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    def test_story_points_field_default(self):
        """story_points_field defaults to customfield_10016."""
        integration = JiraIntegrationFactory(team=self.team)
        self.assertEqual(integration.story_points_field, "customfield_10016")

    def test_story_points_field_custom(self):
        """story_points_field can be customized."""
        integration = JiraIntegrationFactory(
            team=self.team,
            story_points_field="customfield_10025"
        )
        self.assertEqual(integration.story_points_field, "customfield_10025")
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest apps/integrations/tests/test_models.py::JiraIntegrationStoryPointsFieldTest -v
```

Expected: FAIL with `TypeError` (unexpected keyword argument)

**Step 3: Add field to JiraIntegration model**

Edit `apps/integrations/models/jira.py`, add to `JiraIntegration` class:

```python
    story_points_field = models.CharField(
        max_length=50,
        default="customfield_10016",
        verbose_name="Story Points Field",
        help_text="Jira custom field ID for story points (varies by Jira instance)",
    )
```

**Step 4: Create and run migration**

```bash
.venv/bin/python manage.py makemigrations integrations --name jira_story_points_field
.venv/bin/python manage.py migrate integrations
```

**Step 5: Run test to verify it passes**

```bash
.venv/bin/pytest apps/integrations/tests/test_models.py::JiraIntegrationStoryPointsFieldTest -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add apps/integrations/models/jira.py apps/integrations/migrations/*story_points_field*
git commit -m "feat(jira): add configurable story_points_field to JiraIntegration

Default to customfield_10016, allows team admin to override
for Jira instances using different custom fields"
```

---

## Phase 2: Core Services

### Task 4: Implement changelog parsing service

**Files:**
- Create: `apps/integrations/services/jira_changelog.py`
- Test: `apps/integrations/tests/test_jira_changelog.py`

**Step 1: Write the failing tests**

Create `apps/integrations/tests/test_jira_changelog.py`:

```python
"""Tests for Jira changelog parsing."""
from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.services.jira_changelog import parse_changelog_to_time_in_status


class ParseChangelogTest(TestCase):
    """Tests for parse_changelog_to_time_in_status function."""

    def test_empty_changelog(self):
        """Empty changelog returns empty dict and zero transitions."""
        changelog = {"histories": []}
        time_in_status, transitions = parse_changelog_to_time_in_status(
            changelog, current_status="Done"
        )
        self.assertEqual(time_in_status, {})
        self.assertEqual(transitions, 0)

    def test_single_transition(self):
        """Single status transition calculates time correctly."""
        now = timezone.now()
        changelog = {
            "histories": [
                {
                    "created": (now - timedelta(hours=8)).isoformat(),
                    "items": [
                        {"field": "status", "fromString": "To Do", "toString": "In Progress"}
                    ]
                }
            ]
        }

        with patch("apps.integrations.services.jira_changelog.timezone.now", return_value=now):
            time_in_status, transitions = parse_changelog_to_time_in_status(
                changelog, current_status="In Progress"
            )

        self.assertEqual(transitions, 1)
        # Should have ~8 hours in "In Progress" (current status)
        self.assertAlmostEqual(time_in_status.get("In Progress", 0), 8.0, delta=0.1)

    def test_normal_flow(self):
        """Normal workflow: To Do -> In Progress -> Review -> Done."""
        now = timezone.now()
        changelog = {
            "histories": [
                {
                    "created": (now - timedelta(hours=24)).isoformat(),
                    "items": [
                        {"field": "status", "fromString": "To Do", "toString": "In Progress"}
                    ]
                },
                {
                    "created": (now - timedelta(hours=16)).isoformat(),
                    "items": [
                        {"field": "status", "fromString": "In Progress", "toString": "Code Review"}
                    ]
                },
                {
                    "created": (now - timedelta(hours=4)).isoformat(),
                    "items": [
                        {"field": "status", "fromString": "Code Review", "toString": "Done"}
                    ]
                }
            ]
        }

        with patch("apps.integrations.services.jira_changelog.timezone.now", return_value=now):
            time_in_status, transitions = parse_changelog_to_time_in_status(
                changelog, current_status="Done"
            )

        self.assertEqual(transitions, 3)
        # In Progress: 24h - 16h = 8h
        self.assertAlmostEqual(time_in_status.get("In Progress", 0), 8.0, delta=0.1)
        # Code Review: 16h - 4h = 12h
        self.assertAlmostEqual(time_in_status.get("Code Review", 0), 12.0, delta=0.1)
        # Done: 4h (from last transition to now)
        self.assertAlmostEqual(time_in_status.get("Done", 0), 4.0, delta=0.1)

    def test_circular_transitions_accumulate(self):
        """Circular transitions (rework) accumulate time per status."""
        now = timezone.now()
        changelog = {
            "histories": [
                {
                    "created": (now - timedelta(hours=20)).isoformat(),
                    "items": [
                        {"field": "status", "fromString": "To Do", "toString": "In Progress"}
                    ]
                },
                {
                    "created": (now - timedelta(hours=16)).isoformat(),
                    "items": [
                        {"field": "status", "fromString": "In Progress", "toString": "Review"}
                    ]
                },
                {
                    "created": (now - timedelta(hours=12)).isoformat(),
                    "items": [
                        {"field": "status", "fromString": "Review", "toString": "In Progress"}
                    ]
                },
                {
                    "created": (now - timedelta(hours=8)).isoformat(),
                    "items": [
                        {"field": "status", "fromString": "In Progress", "toString": "Done"}
                    ]
                }
            ]
        }

        with patch("apps.integrations.services.jira_changelog.timezone.now", return_value=now):
            time_in_status, transitions = parse_changelog_to_time_in_status(
                changelog, current_status="Done"
            )

        self.assertEqual(transitions, 4)
        # In Progress: (20-16) + (12-8) = 4 + 4 = 8h total
        self.assertAlmostEqual(time_in_status.get("In Progress", 0), 8.0, delta=0.1)
        # Review: 16-12 = 4h
        self.assertAlmostEqual(time_in_status.get("Review", 0), 4.0, delta=0.1)

    def test_ignores_non_status_changes(self):
        """Only status field changes are counted."""
        now = timezone.now()
        changelog = {
            "histories": [
                {
                    "created": (now - timedelta(hours=8)).isoformat(),
                    "items": [
                        {"field": "assignee", "fromString": "Alice", "toString": "Bob"},
                        {"field": "status", "fromString": "To Do", "toString": "In Progress"},
                        {"field": "priority", "fromString": "Medium", "toString": "High"},
                    ]
                }
            ]
        }

        time_in_status, transitions = parse_changelog_to_time_in_status(
            changelog, current_status="In Progress"
        )

        # Only 1 status transition, not 3
        self.assertEqual(transitions, 1)
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest apps/integrations/tests/test_jira_changelog.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement the changelog parsing service**

Create `apps/integrations/services/jira_changelog.py`:

```python
"""Jira changelog parsing for time-in-status tracking.

Parses Jira issue changelog to calculate time spent in each status.
Only extracts status field changes (not assignee, priority, etc.).
"""
from collections import defaultdict
from datetime import datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime


def parse_changelog_to_time_in_status(
    changelog: dict, current_status: str
) -> tuple[dict[str, float], int]:
    """Parse Jira changelog to calculate time spent in each status.

    Args:
        changelog: Jira changelog response containing 'histories' list
        current_status: Issue's current status (for calculating time since last transition)

    Returns:
        Tuple of (time_in_status dict, status_transitions count)
        time_in_status maps status names to hours spent in that status
        Example: ({"In Progress": 12.5, "Code Review": 18.0}, 4)
    """
    time_in_status: dict[str, float] = defaultdict(float)

    # Extract only status field changes
    status_changes: list[dict] = []
    for history in changelog.get("histories", []):
        for item in history.get("items", []):
            if item.get("field") == "status":
                timestamp = _parse_timestamp(history.get("created"))
                if timestamp:
                    status_changes.append({
                        "timestamp": timestamp,
                        "from_status": item.get("fromString"),
                        "to_status": item.get("toString"),
                    })

    transitions = len(status_changes)

    if not status_changes:
        return dict(time_in_status), transitions

    # Sort by timestamp (oldest first)
    status_changes.sort(key=lambda x: x["timestamp"])

    # Calculate time between each transition
    for i in range(len(status_changes)):
        change = status_changes[i]

        if i == 0:
            # First transition: can't calculate time in previous status
            # (we don't know when issue was created in that status)
            continue

        prev_change = status_changes[i - 1]
        prev_status = prev_change["to_status"]

        # Time from previous transition to this one
        duration_hours = (change["timestamp"] - prev_change["timestamp"]).total_seconds() / 3600
        time_in_status[prev_status] += duration_hours

    # Add time in current status (from last transition to now)
    if status_changes:
        last_change = status_changes[-1]
        last_status = last_change["to_status"]
        hours_in_current = (timezone.now() - last_change["timestamp"]).total_seconds() / 3600
        time_in_status[last_status] += hours_in_current

    # Round to 1 decimal place
    return {k: round(v, 1) for k, v in time_in_status.items()}, transitions


def _parse_timestamp(timestamp_str: str | None) -> datetime | None:
    """Parse ISO timestamp string to datetime."""
    if not timestamp_str:
        return None

    # Handle Jira's ISO format (may include timezone)
    parsed = parse_datetime(timestamp_str)
    if parsed and parsed.tzinfo is None:
        # Make timezone-aware if not already
        parsed = timezone.make_aware(parsed)
    return parsed
```

**Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest apps/integrations/tests/test_jira_changelog.py -v
```

Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add apps/integrations/services/jira_changelog.py apps/integrations/tests/test_jira_changelog.py
git commit -m "feat(jira): implement changelog parsing for time-in-status

- parse_changelog_to_time_in_status() extracts status changes only
- Calculates hours spent in each status
- Handles circular transitions (rework) by accumulating time
- Returns transition count as rework indicator"
```

---

### Task 5: Implement feature gating helper

**Files:**
- Modify: `apps/integrations/services/jira_utils.py`
- Test: `apps/integrations/tests/test_jira_utils.py`

**Step 1: Write the failing tests**

Add to `apps/integrations/tests/test_jira_utils.py`:

```python
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.integrations.factories import JiraIntegrationFactory
from apps.integrations.services.jira_utils import should_include_jira_context
from apps.metrics.factories import JiraIssueFactory, TeamFactory


class ShouldIncludeJiraContextTest(TestCase):
    """Tests for should_include_jira_context gating function."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    def test_returns_false_when_flag_disabled(self):
        """Returns False when feature flag is off."""
        # Create full setup
        JiraIntegrationFactory(team=self.team)
        JiraIssueFactory(team=self.team)

        with patch("apps.integrations.services.jira_utils.flag_is_active", return_value=False):
            result = should_include_jira_context(self.team)

        self.assertFalse(result)

    def test_returns_false_when_no_integration(self):
        """Returns False when team has no Jira integration."""
        # No JiraIntegration created
        with patch("apps.integrations.services.jira_utils.flag_is_active", return_value=True):
            result = should_include_jira_context(self.team)

        self.assertFalse(result)

    def test_returns_false_when_no_synced_data(self):
        """Returns False when integration exists but no issues synced."""
        JiraIntegrationFactory(team=self.team)
        # No JiraIssue created

        with patch("apps.integrations.services.jira_utils.flag_is_active", return_value=True):
            result = should_include_jira_context(self.team)

        self.assertFalse(result)

    def test_returns_true_when_all_conditions_met(self):
        """Returns True when flag on, integration exists, and data synced."""
        JiraIntegrationFactory(team=self.team)
        JiraIssueFactory(team=self.team)

        with patch("apps.integrations.services.jira_utils.flag_is_active", return_value=True):
            result = should_include_jira_context(self.team)

        self.assertTrue(result)
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest apps/integrations/tests/test_jira_utils.py::ShouldIncludeJiraContextTest -v
```

Expected: FAIL with `ImportError` or `AttributeError`

**Step 3: Implement the gating function**

Add to `apps/integrations/services/jira_utils.py`:

```python
def should_include_jira_context(team) -> bool:
    """Check if Jira data should be included for this team.

    Returns True only when ALL conditions are met:
    1. Feature flag 'integration_jira_enabled' is active
    2. Team has a JiraIntegration record
    3. Team has at least one JiraIssue synced

    Args:
        team: Team model instance

    Returns:
        True if Jira context should be included, False otherwise
    """
    from waffle import flag_is_active

    from apps.integrations.models import JiraIntegration
    from apps.metrics.models import JiraIssue

    # Check feature flag
    if not flag_is_active("integration_jira_enabled"):
        return False

    # Check team has Jira connected
    if not JiraIntegration.objects.filter(team=team).exists():
        return False

    # Check team has synced Jira data
    if not JiraIssue.objects.filter(team=team).exists():
        return False

    return True
```

**Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest apps/integrations/tests/test_jira_utils.py::ShouldIncludeJiraContextTest -v
```

Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add apps/integrations/services/jira_utils.py apps/integrations/tests/test_jira_utils.py
git commit -m "feat(jira): add should_include_jira_context() gating helper

Checks feature flag + integration exists + data synced
before including Jira context in LLM prompts or dashboards"
```

---

### Task 6: Implement ADF-to-text converter for Jira descriptions

**Files:**
- Create: `apps/integrations/services/jira_adf.py`
- Test: `apps/integrations/tests/test_jira_adf.py`

**Step 1: Write the failing tests**

Create `apps/integrations/tests/test_jira_adf.py`:

```python
"""Tests for Atlassian Document Format (ADF) to text conversion."""
from django.test import TestCase

from apps.integrations.services.jira_adf import adf_to_text


class ADFToTextTest(TestCase):
    """Tests for adf_to_text converter."""

    def test_none_returns_empty_string(self):
        """None input returns empty string."""
        self.assertEqual(adf_to_text(None), "")

    def test_string_returns_unchanged(self):
        """Plain string input is returned unchanged (legacy format)."""
        self.assertEqual(adf_to_text("Plain text description"), "Plain text description")

    def test_simple_paragraph(self):
        """Simple paragraph extracts text."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "This is a paragraph."}
                    ]
                }
            ]
        }
        self.assertEqual(adf_to_text(adf), "This is a paragraph.")

    def test_multiple_paragraphs(self):
        """Multiple paragraphs joined with newlines."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "First paragraph."}]
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Second paragraph."}]
                }
            ]
        }
        self.assertEqual(adf_to_text(adf), "First paragraph.\nSecond paragraph.")

    def test_bullet_list(self):
        """Bullet list items extracted with markers."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Item 1"}]
                                }
                            ]
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Item 2"}]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        result = adf_to_text(adf)
        self.assertIn("Item 1", result)
        self.assertIn("Item 2", result)

    def test_code_block(self):
        """Code block content extracted."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "codeBlock",
                    "content": [
                        {"type": "text", "text": "def hello():\n    print('hi')"}
                    ]
                }
            ]
        }
        result = adf_to_text(adf)
        self.assertIn("def hello()", result)

    def test_heading(self):
        """Headings extracted."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Section Title"}]
                }
            ]
        }
        result = adf_to_text(adf)
        self.assertIn("Section Title", result)

    def test_empty_doc(self):
        """Empty document returns empty string."""
        adf = {"type": "doc", "content": []}
        self.assertEqual(adf_to_text(adf), "")
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest apps/integrations/tests/test_jira_adf.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement the ADF converter**

Create `apps/integrations/services/jira_adf.py`:

```python
"""Atlassian Document Format (ADF) to plain text converter.

Jira Cloud returns descriptions as ADF (JSON structure), not plain text.
This module extracts readable text from ADF for LLM prompts and display.

Reference: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/
"""


def adf_to_text(adf_content: dict | str | None) -> str:
    """Convert Atlassian Document Format to plain text.

    Args:
        adf_content: ADF document dict, plain string (legacy), or None

    Returns:
        Plain text extracted from the document
    """
    if adf_content is None:
        return ""

    # Handle legacy plain text format (Jira Server or old issues)
    if isinstance(adf_content, str):
        return adf_content

    if not isinstance(adf_content, dict):
        return str(adf_content)

    # ADF document structure
    if adf_content.get("type") != "doc":
        return ""

    content = adf_content.get("content", [])
    if not content:
        return ""

    lines = []
    for node in content:
        text = _extract_node_text(node)
        if text:
            lines.append(text)

    return "\n".join(lines)


def _extract_node_text(node: dict) -> str:
    """Extract text from a single ADF node."""
    if not isinstance(node, dict):
        return ""

    node_type = node.get("type", "")

    # Text node - leaf node with actual text
    if node_type == "text":
        return node.get("text", "")

    # Paragraph - inline content
    if node_type == "paragraph":
        return _extract_inline_text(node.get("content", []))

    # Heading - inline content
    if node_type == "heading":
        return _extract_inline_text(node.get("content", []))

    # Code block - plain text content
    if node_type == "codeBlock":
        return _extract_inline_text(node.get("content", []))

    # List items
    if node_type in ("bulletList", "orderedList"):
        items = []
        for item in node.get("content", []):
            if item.get("type") == "listItem":
                item_text = _extract_list_item_text(item)
                if item_text:
                    marker = "•" if node_type == "bulletList" else "-"
                    items.append(f"{marker} {item_text}")
        return "\n".join(items)

    # Block quote
    if node_type == "blockquote":
        content = node.get("content", [])
        texts = [_extract_node_text(child) for child in content]
        return "\n".join(t for t in texts if t)

    # Table - simplified extraction
    if node_type == "table":
        rows = []
        for row in node.get("content", []):
            if row.get("type") == "tableRow":
                cells = []
                for cell in row.get("content", []):
                    cell_text = _extract_inline_text(cell.get("content", []))
                    cells.append(cell_text)
                rows.append(" | ".join(cells))
        return "\n".join(rows)

    # Media, emoji, etc. - skip or placeholder
    if node_type in ("media", "mediaGroup", "mediaSingle"):
        return "[media]"

    if node_type == "emoji":
        return node.get("attrs", {}).get("shortName", "")

    # Recursively process unknown nodes with content
    if "content" in node:
        texts = [_extract_node_text(child) for child in node.get("content", [])]
        return "\n".join(t for t in texts if t)

    return ""


def _extract_inline_text(content: list) -> str:
    """Extract text from inline content (paragraph, heading, etc.)."""
    if not content:
        return ""

    texts = []
    for item in content:
        if isinstance(item, dict):
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif item.get("type") == "hardBreak":
                texts.append("\n")
            elif item.get("type") == "mention":
                texts.append(f"@{item.get('attrs', {}).get('text', 'user')}")
            elif item.get("type") == "emoji":
                texts.append(item.get("attrs", {}).get("shortName", ""))
            elif "content" in item:
                texts.append(_extract_inline_text(item.get("content", [])))

    return "".join(texts)


def _extract_list_item_text(item: dict) -> str:
    """Extract text from a list item node."""
    content = item.get("content", [])
    texts = []
    for child in content:
        text = _extract_node_text(child)
        if text:
            texts.append(text)
    return " ".join(texts)
```

**Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest apps/integrations/tests/test_jira_adf.py -v
```

Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add apps/integrations/services/jira_adf.py apps/integrations/tests/test_jira_adf.py
git commit -m "feat(jira): add ADF-to-text converter for Jira descriptions

Jira Cloud returns descriptions as Atlassian Document Format (JSON).
This converter extracts plain text for LLM prompts and display."
```

---

### Task 7: Implement Jira key validation

**Files:**
- Modify: `apps/integrations/services/jira_utils.py`
- Test: `apps/integrations/tests/test_jira_utils.py`

**Step 1: Write the failing tests**

Add to `apps/integrations/tests/test_jira_utils.py`:

```python
from apps.integrations.factories import TrackedJiraProjectFactory


class ValidateJiraKeyTest(TestCase):
    """Tests for validate_jira_key function."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        # Create tracked project with key "PROJ"
        cls.tracked_project = TrackedJiraProjectFactory(
            team=cls.team,
            project_key="PROJ",
            is_active=True
        )

    def test_valid_key_from_tracked_project(self):
        """Returns True for key from tracked project."""
        from apps.integrations.services.jira_utils import validate_jira_key

        result = validate_jira_key(self.team, "PROJ-123")
        self.assertTrue(result)

    def test_invalid_key_not_tracked(self):
        """Returns False for key from non-tracked project."""
        from apps.integrations.services.jira_utils import validate_jira_key

        result = validate_jira_key(self.team, "OTHER-456")
        self.assertFalse(result)

    def test_inactive_project_returns_false(self):
        """Returns False for key from inactive project."""
        from apps.integrations.services.jira_utils import validate_jira_key

        # Deactivate the project
        self.tracked_project.is_active = False
        self.tracked_project.save()

        result = validate_jira_key(self.team, "PROJ-789")
        self.assertFalse(result)

        # Restore
        self.tracked_project.is_active = True
        self.tracked_project.save()

    def test_malformed_key_returns_false(self):
        """Returns False for malformed Jira key."""
        from apps.integrations.services.jira_utils import validate_jira_key

        result = validate_jira_key(self.team, "invalid")
        self.assertFalse(result)

    def test_empty_key_returns_false(self):
        """Returns False for empty key."""
        from apps.integrations.services.jira_utils import validate_jira_key

        result = validate_jira_key(self.team, "")
        self.assertFalse(result)
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest apps/integrations/tests/test_jira_utils.py::ValidateJiraKeyTest -v
```

Expected: FAIL with `ImportError`

**Step 3: Implement validate_jira_key**

Add to `apps/integrations/services/jira_utils.py`:

```python
def validate_jira_key(team, jira_key: str) -> bool:
    """Check if Jira key belongs to a tracked project for this team.

    Args:
        team: Team model instance
        jira_key: Jira issue key (e.g., "PROJ-123")

    Returns:
        True if key's project prefix matches an active tracked project
    """
    from apps.integrations.models import TrackedJiraProject

    if not jira_key or "-" not in jira_key:
        return False

    # Extract project prefix (e.g., "PROJ" from "PROJ-123")
    project_prefix = jira_key.split("-")[0]

    return TrackedJiraProject.objects.filter(
        team=team,
        project_key=project_prefix,
        is_active=True
    ).exists()
```

**Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest apps/integrations/tests/test_jira_utils.py::ValidateJiraKeyTest -v
```

Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add apps/integrations/services/jira_utils.py apps/integrations/tests/test_jira_utils.py
git commit -m "feat(jira): add validate_jira_key() to check tracked projects

Only link PRs to Jira keys from actively tracked projects"
```

---

## Phase 3: Jira Sync Enhancement

### Task 8: Update JiraIssueFactory with new fields

**Files:**
- Modify: `apps/metrics/factories.py`

**Step 1: Verify current factory works**

```bash
.venv/bin/pytest apps/metrics/tests/models/test_jira_issue.py -v
```

Expected: Tests pass (from Task 1)

**Step 2: Update JiraIssueFactory**

Find `JiraIssueFactory` in `apps/metrics/factories.py` and update to include new fields:

```python
class JiraIssueFactory(DjangoModelFactory):
    """Factory for JiraIssue model."""

    class Meta:
        model = JiraIssue

    team = factory.SubFactory(TeamFactory)
    jira_key = factory.Sequence(lambda n: f"PROJ-{n}")
    jira_id = factory.Sequence(lambda n: str(10000 + n))
    summary = factory.Faker("sentence")
    issue_type = factory.Iterator(["Story", "Bug", "Task"])
    status = "Done"
    description = factory.Faker("paragraph")
    labels = factory.LazyFunction(lambda: ["backend", "feature"])
    priority = factory.Iterator(["High", "Medium", "Low"])
    story_points = factory.LazyFunction(lambda: Decimal(random.choice([1, 2, 3, 5, 8, 13])))
    issue_created_at = factory.LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 30)))
    resolved_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=random.randint(1, 48)))
    cycle_time_hours = factory.LazyFunction(lambda: Decimal(random.uniform(4, 72)))

    # New fields for time-in-status tracking
    time_in_status = factory.LazyFunction(lambda: {
        "In Progress": round(random.uniform(2, 20), 1),
        "Code Review": round(random.uniform(1, 10), 1),
    })
    status_transitions = factory.LazyFunction(lambda: random.randint(2, 6))

    class Params:
        no_story_points = factory.Trait(story_points=None)
        complex_history = factory.Trait(
            time_in_status={
                "To Do": 2.0,
                "In Progress": 8.0,
                "Code Review": 12.0,
                "QA": 4.0,
            },
            status_transitions=5
        )
        no_transitions = factory.Trait(
            time_in_status={},
            status_transitions=0
        )
        quick_resolution = factory.Trait(
            time_in_status={"In Progress": 1.0},
            status_transitions=1,
            cycle_time_hours=Decimal("2.0")
        )
```

**Step 3: Test factory works**

```bash
.venv/bin/pytest apps/metrics/tests/models/test_jira_issue.py -v
```

Expected: All tests PASS

**Step 4: Commit**

```bash
git add apps/metrics/factories.py
git commit -m "feat(jira): update JiraIssueFactory with time_in_status fields

Add traits for testing: no_story_points, complex_history,
no_transitions, quick_resolution"
```

---

## Continue with remaining phases...

This plan continues with:

**Phase 3 (continued):**
- Task 9: Update jira_client.py with dynamic SP field and retry logic
- Task 10: Update jira_sync.py with changelog fetching
- Task 11: Add phased sync (30d/60d) support

**Phase 4: LLM Integration:**
- Task 12: Add Jira parameters to render_pr_user_prompt()
- Task 13: Update pr_analysis/user.jinja2 template
- Task 14: Add _get_jira_context_for_pr() helper
- Task 15: Update insight template
- Task 16: Add dynamic token budget

**Phase 5: Dashboard:**
- Task 17: Add linkage rate service function
- Task 18: Update overview dashboard view
- Task 19: Add linkage indicator component
- Task 20: Update team analytics view

**Phase 6: Onboarding:**
- Task 21: Add Jira sync phases to pipeline
- Task 22: Update sync_status() endpoint
- Task 23: Update sync_progress.html template

---

## Verification Checklist

Before marking complete, verify:

- [ ] All migrations applied successfully
- [ ] `pytest apps/integrations/tests/test_jira_*.py -v` passes
- [ ] `pytest apps/metrics/tests/ -k jira -v` passes
- [ ] Feature flag `integration_jira_enabled` works
- [ ] Manual test: Connect Jira, sync, verify time_in_status populated
- [ ] Manual test: Dashboard shows linkage rate
- [ ] Manual test: PR detail shows Jira card

---

## Rollback Plan

If issues arise:

1. Disable feature flag `integration_jira_enabled`
2. All Jira-enriched views gracefully degrade to existing behavior
3. No data migration rollback needed (new fields have defaults)
