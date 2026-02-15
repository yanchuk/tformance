---
name: factory-pattern-guide
description: Guide for using Factory Boy factories in tests. Triggers on test writing, factory usage, TestCase setup, test data creation, setUp method. Covers factory locations, Sequence for unique fields, build vs create, batch creation.
---

# Factory Pattern Guide

## Purpose

Provide guidance on using Factory Boy factories for test data creation in Django tests.

## When to Use

**Automatically activates when:**
- Writing Django tests
- Creating test fixtures
- Setting up test data in `setUp()` methods
- Avoiding database constraint violations

## Factory Locations

```python
# Main factories
from apps.metrics.factories import (
    PullRequestFactory, TeamMemberFactory, PRReviewFactory,
    CommitFactory, PRFileFactory, JiraIssueFactory,
    AIUsageDailyFactory, PRSurveyFactory, WeeklyMetricsFactory,
)
from apps.teams.factories import TeamFactory
from apps.users.factories import CustomUserFactory
from apps.integrations.factories import ConnectedAccountFactory
```

## Basic Usage

### Create (saves to DB)

```python
team = TeamFactory()
member = TeamMemberFactory(team=team)
pr = PullRequestFactory(team=team, author=member, state='merged')
```

### Build (no DB save)

```python
pr = PullRequestFactory.build()  # For unit tests
```

### Batch Creation

```python
prs = PullRequestFactory.create_batch(10, team=team, state='merged')
```

## Handling Unique Fields

Use `factory.Sequence` to avoid constraint violations:

```python
import factory

class TeamMemberFactory(factory.django.DjangoModelFactory):
    github_id = factory.Sequence(lambda n: str(10000 + n))
    github_username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
```

## Test Structure

```python
from django.test import TestCase
from apps.metrics.factories import TeamMemberFactory, PullRequestFactory
from apps.teams.factories import TeamFactory


class TestFeatureName(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_specific_behavior(self):
        # Arrange
        pr = PullRequestFactory(team=self.team, author=self.member)

        # Act
        result = some_function(pr)

        # Assert
        self.assertEqual(result, expected)
```

## Available Factories

| Factory | Key Fields |
|---------|------------|
| `TeamFactory` | name, slug |
| `TeamMemberFactory` | team, github_username, role |
| `PullRequestFactory` | team, author, state, is_ai_assisted |
| `PRReviewFactory` | pull_request, reviewer, state |
| `CommitFactory` | pull_request, author, sha |
| `PRFileFactory` | pull_request, filename, file_category |
| `JiraIssueFactory` | team, key, summary, status |
| `AIUsageDailyFactory` | team, member, date, tool |
| `PRSurveyFactory` | pull_request, respondent |
| `WeeklyMetricsFactory` | team, member, week_start |

## Common Mistakes

### ❌ Manual Model Creation

```python
pr = PullRequest.objects.create(team=team, github_id='123', ...)
```

### ✅ Use Factory

```python
pr = PullRequestFactory(team=team)
```

### ❌ Hardcoded Unique Values

```python
member = TeamMemberFactory(github_id='12345')  # Fails on 2nd run
```

### ✅ Let Sequence Handle It

```python
member = TeamMemberFactory()  # github_id auto-generated
```

## Quick Reference

| Method | Saves to DB | Use Case |
|--------|-------------|----------|
| `Factory()` | Yes | Integration tests |
| `Factory.build()` | No | Unit tests |
| `Factory.create_batch(n)` | Yes | Multiple instances |
| `Factory.build_batch(n)` | No | Multiple without DB |

---

**Enforcement Level**: SUGGEST
**Priority**: High
