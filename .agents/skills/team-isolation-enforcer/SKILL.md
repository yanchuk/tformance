---
name: team-isolation-enforcer
description: Enforces team isolation patterns on BaseTeamModel queries. Triggers on model queries, filter(), get(), all() on team-owned models. Prevents TEAM001 violations and tenant data leakage. Critical for multi-tenant security.
---

# Team Isolation Enforcer

## Purpose

Prevent tenant data leakage by ensuring all queries on `BaseTeamModel` subclasses include proper team filtering.

## When to Use

**Automatically activates when:**
- Writing queries on team-owned models (PullRequest, TeamMember, JiraIssue, etc.)
- Using `Model.objects.filter()`, `.get()`, `.all()` without team context
- Implementing views, services, or Celery tasks that access team data

## Critical Rule

**All `BaseTeamModel` subclasses MUST use team-scoped queries.**

## Safe Query Patterns

### 1. Using `for_team` Manager (Preferred)

```python
# ✅ CORRECT - Uses team-scoped manager
prs = PullRequest.for_team.filter(state='merged')
member = TeamMember.for_team.get(github_username='johndoe')
```

### 2. Explicit Team Filter

```python
# ✅ CORRECT - Explicit team filter
prs = PullRequest.objects.filter(team=team, state='merged')
member = TeamMember.objects.get(team=team, id=member_id)
```

### 3. Related Object Filtering

```python
# ✅ CORRECT - Filtering through team-scoped relation
reviews = PRReview.objects.filter(pull_request__in=team_scoped_prs)
commits = Commit.objects.filter(pull_request__team=team)
```

## Unsafe Patterns (TEAM001 Violations)

```python
# ❌ WRONG - No team filter, could leak data across tenants
prs = PullRequest.objects.filter(state='merged')
member = TeamMember.objects.get(github_username='johndoe')
all_prs = PullRequest.objects.all()
```

## BaseTeamModel Subclasses

These models REQUIRE team filtering:

| Model | App |
|-------|-----|
| `TeamMember` | metrics |
| `PullRequest` | metrics |
| `PRReview` | metrics |
| `PRFile` | metrics |
| `Commit` | metrics |
| `JiraIssue` | metrics |
| `PRSurvey` | metrics |
| `AIUsageDaily` | metrics |
| `WeeklyMetrics` | metrics |
| `ConnectedAccount` | integrations |

## Suppression (Use Sparingly)

```python
# noqa: TEAM001 - ID from Celery task queue (trusted source)
pr = PullRequest.objects.get(id=pr_id)
```

**Valid suppression reasons:**
- Celery tasks with IDs from trusted queue
- Webhook handlers with verified external IDs
- Admin operations with explicit permission check

## Linting

```bash
make lint-team-isolation        # Production code
make lint-team-isolation-all    # Include tests
```

## Quick Reference

| Pattern | Safe? |
|---------|-------|
| `Model.for_team.filter(...)` | ✅ |
| `Model.objects.filter(team=team, ...)` | ✅ |
| `Model.objects.filter(related__team=team)` | ✅ |
| `Model.objects.filter(...)` | ❌ |
| `Model.objects.all()` | ❌ |
| `Model.objects.get(id=id)` | ⚠️ noqa only |

---

**Enforcement Level**: BLOCK
**Priority**: Critical
