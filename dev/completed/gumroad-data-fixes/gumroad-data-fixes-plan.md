# Gumroad Data Display Fixes - Implementation Plan

**Last Updated:** 2025-12-23

## Executive Summary

Gumroad data was successfully seeded from GitHub but isn't displaying correctly on dashboards due to:
1. Date range (68+ days old, outside default 7-day view)
2. Iteration metrics not calculated during seeding
3. AI co-author parsing not run on existing commits
4. Copilot display showing all 13 users (too many)

## Current State Analysis

### Database Analysis Results

| Metric | Value | Notes |
|--------|-------|-------|
| Total PRs | 224 | 96 merged, 128 closed |
| Date Range | Aug 27 - Oct 16, 2025 | **68+ days old** |
| PRs in last 7 days | 0 | Data too old |
| PRs in last 30 days | 0 | Data too old |
| PRs in last 90 days | 84 | Within window |
| AI-Assisted PRs | 4 | is_ai_assisted=True |
| PRs with ai_tools_detected | 4 | copilot:3, ai_generic:1 |
| Total Reviews | 161 | Across 101 PRs |
| Weekly Metrics | 5 weeks | Aug 25 - Oct 13 |
| Copilot Users | 13 | 175,740 total suggestions |

### Root Causes Identified

#### 1. Date Range Issue (Critical)
**Problem:** PR data spans Aug 27 - Oct 16, 2025. Today is Dec 23, 2025 (68+ days gap).
- 7-day view: Shows 0 PRs (correct - no data in range)
- 30-day view: Shows 0 PRs (correct - no data in range)
- 90-day view: Shows 91 PRs (data within window)

**Impact:** `/app/` dashboard defaults to 7-day view, showing empty stats.

#### 2. Iteration Metrics Not Seeded
**Problem:** All 96 merged PRs have NULL for iteration fields:
- `review_rounds`: 0 PRs populated
- `avg_fix_response_hours`: 0 PRs populated
- `commits_after_first_review`: 0 PRs populated
- `total_comments`: 0 PRs populated

**Impact:** "Iteration Metrics" section shows "No data" for all fields.

#### 3. Commit AI Co-Authors Not Parsed
**Problem:** Commits have co-author data in messages but fields not populated:
- `ai_co_authors`: 0 commits with data (field is empty JSONB)
- `is_ai_assisted` on commits: 0 commits flagged

**Evidence:** Found 11+ commits with `Co-authored-by:` in messages:
- `autofix-ci[bot]`
- Human co-authors (Emmanuel Cousin, Jono M, Maya)

**Impact:** "Auto-Detection Rate" shows 0% despite having co-authored commits.

#### 4. Devin Bot Detection Missing
**Problem:** No detection for Devin bot PRs or other AI coding agents.
- Current detection: copilot, ai_generic, claude_code, cursor, cody
- Missing: devin, aider (as PR author), windsurf

#### 5. Copilot Display Too Long
**Problem:** Copilot Usage by Member shows all 13 active users.
**Request:** Limit to top 5 users to reduce visual clutter.

## Proposed Future State

After implementation:
- `/app/` dashboard shows data on 7-day, 30-day, and 90-day views
- Copilot section shows top 5 users only
- Iteration Metrics section displays calculated values
- AI Detection shows accurate auto-detection rate
- Devin bot PRs are correctly flagged as AI-assisted

## Implementation Phases

### Phase 1: Date Range Fix (Effort: M)

Create management command to shift all Gumroad dates forward.

**Files:**
- Create: `apps/metrics/management/commands/fix_gumroad_dates.py`

**Implementation:**

```python
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.metrics.models import (
    AIUsageDaily, Commit, PRReview, PullRequest, WeeklyMetrics
)
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Shift Gumroad demo data dates to fall within dashboard windows"

    def add_arguments(self, parser):
        parser.add_argument("--team", type=str, default="Gumroad")
        parser.add_argument("--days", type=int, default=68)
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        team = Team.objects.get(name=options["team"])
        days = timedelta(days=options["days"])
        dry_run = options["dry_run"]

        # Shift PRs
        prs = PullRequest.objects.filter(team=team)
        for pr in prs:
            if pr.merged_at:
                pr.merged_at += days
            if pr.pr_created_at:
                pr.pr_created_at += days
            if pr.first_review_at:
                pr.first_review_at += days
            if not dry_run:
                pr.save()
        self.stdout.write(f"Shifted {prs.count()} PRs")

        # Shift Reviews
        reviews = PRReview.objects.filter(team=team)
        for review in reviews:
            if review.submitted_at:
                review.submitted_at += days
            if not dry_run:
                review.save()
        self.stdout.write(f"Shifted {reviews.count()} reviews")

        # Shift Commits
        commits = Commit.objects.filter(team=team)
        for commit in commits:
            if commit.committed_at:
                commit.committed_at += days
            if not dry_run:
                commit.save()
        self.stdout.write(f"Shifted {commits.count()} commits")

        # Shift WeeklyMetrics
        weekly = WeeklyMetrics.objects.filter(team=team)
        for wm in weekly:
            wm.week_start += days
            if not dry_run:
                wm.save()
        self.stdout.write(f"Shifted {weekly.count()} weekly metrics")

        # Shift AI Usage
        ai_usage = AIUsageDaily.objects.filter(team=team)
        for au in ai_usage:
            au.date += days
            if not dry_run:
                au.save()
        self.stdout.write(f"Shifted {ai_usage.count()} AI usage records")
```

**Acceptance Criteria:**
- PRs appear on 7-day dashboard view
- All related dates shifted proportionally
- Command is idempotent (safe to run multiple times)

### Phase 2: Copilot Display Limit (Effort: XS)

**Files:**
- Modify: `apps/metrics/services/dashboard_service.py`

**Implementation:**

```python
def get_copilot_by_member(
    team: Team, start_date: date, end_date: date, limit: int = 5
) -> list[dict]:
    """Get Copilot metrics breakdown by member.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        limit: Maximum number of members to return (default 5)
    """
    # ... existing query ...
    return result[:limit]
```

**Acceptance Criteria:**
- Copilot Usage by Member shows only top 5 users
- Other callers can still get more if needed

### Phase 3: AI Co-Author Parsing (Effort: M)

**Files:**
- Create: `apps/metrics/management/commands/parse_ai_coauthors.py`

**Implementation:**

```python
from django.core.management.base import BaseCommand
from apps.metrics.models import Commit
from apps.metrics.services.ai_detector import parse_co_authors
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Parse AI co-authors from existing commit messages"

    def add_arguments(self, parser):
        parser.add_argument("--team", type=str, default="Gumroad")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        team = Team.objects.get(name=options["team"])
        dry_run = options["dry_run"]

        commits = Commit.objects.filter(team=team, ai_co_authors=[])
        updated = 0
        ai_found = 0

        for commit in commits:
            result = parse_co_authors(commit.message)
            if result["has_ai_co_authors"]:
                commit.is_ai_assisted = True
                commit.ai_co_authors = result["ai_co_authors"]
                ai_found += 1
                if not dry_run:
                    commit.save()
                updated += 1

        self.stdout.write(f"Processed {commits.count()} commits")
        self.stdout.write(f"Found AI co-authors in {ai_found} commits")
```

**Acceptance Criteria:**
- All commits with AI co-author patterns are flagged
- Auto-Detection Rate shows accurate percentage

### Phase 4: Iteration Metrics Population (Effort: M)

**Files:**
- Create: `apps/metrics/management/commands/calculate_iteration_metrics.py`

**Implementation:**

```python
from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.metrics.models import Commit, PRReview, PullRequest
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Calculate iteration metrics for merged PRs"

    def add_arguments(self, parser):
        parser.add_argument("--team", type=str, default="Gumroad")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        team = Team.objects.get(name=options["team"])
        dry_run = options["dry_run"]

        prs = PullRequest.objects.filter(team=team, state="merged")
        updated = 0

        for pr in prs:
            reviews = PRReview.objects.filter(pull_request=pr).order_by("submitted_at")
            if not reviews.exists():
                continue

            # Review rounds = distinct reviewer count
            pr.review_rounds = reviews.values("reviewer").distinct().count()

            # Commits after first review
            first_review = reviews.first()
            if first_review and first_review.submitted_at:
                pr.commits_after_first_review = Commit.objects.filter(
                    pull_request=pr,
                    committed_at__gt=first_review.submitted_at
                ).count()

            # Total comments (reviews with comments)
            pr.total_comments = reviews.exclude(body="").count()

            if not dry_run:
                pr.save()
            updated += 1

        self.stdout.write(f"Updated {updated} PRs with iteration metrics")
```

**Acceptance Criteria:**
- Iteration Metrics section shows calculated averages
- Reasonable values (not all zeros or nulls)

### Phase 5: Devin Bot Detection (Effort: S)

**Files:**
- Modify: `apps/metrics/services/ai_patterns.py`

**Implementation:**

```python
# Add to AI_REVIEWER_BOTS
AI_REVIEWER_BOTS: dict[str, str] = {
    # ... existing entries ...
    # ----- Devin AI -----
    "devin-ai-integration[bot]": "devin",
    "devin[bot]": "devin",
    "devin-ai[bot]": "devin",
}

# Add to AI_SIGNATURE_PATTERNS
AI_SIGNATURE_PATTERNS: list[tuple[str, str]] = [
    # ... existing entries ...
    # ----- Devin AI -----
    (r"generated\s+by\s+devin", "devin"),
    (r"devin\.ai", "devin"),
    (r"created\s+by\s+devin", "devin"),
]

# Add to AI_CO_AUTHOR_PATTERNS
AI_CO_AUTHOR_PATTERNS: list[tuple[str, str]] = [
    # ... existing entries ...
    # ----- Devin AI -----
    (r"co-authored-by:\s*devin\s*<[^>]+>", "devin"),
    (r"co-authored-by:[^<]*<[^>]*@devin\.ai>", "devin"),
]

# Increment version
PATTERNS_VERSION = "1.1.0"
```

**Acceptance Criteria:**
- Devin bot PRs detected as AI-assisted
- Pattern version incremented for tracking

## Implementation Priority

| Fix | Priority | Effort | Impact |
|-----|----------|--------|--------|
| Shift PR Dates | High | M | Demo works on all date ranges |
| Limit Copilot Top 5 | High | XS | UI improvement |
| Parse Commit AI Co-Authors | Medium | M | Improves auto-detection accuracy |
| Populate Iteration Metrics | Medium | M | Shows iteration section data |
| Devin Bot Detection | Low | S | Future-proofing |

## Success Metrics

After implementation, verify on `/app/metrics/overview/?days=7`:
- PRs Merged shows non-zero value
- Avg Cycle Time shows value
- AI-Assisted shows percentage
- Team Breakdown shows all active members
- Copilot shows top 5 users only
- Iteration Metrics shows data
- Reviewer Workload shows multiple reviewers

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Date shift breaks data integrity | Low | High | Use atomic transaction, test with dry-run first |
| AI patterns match false positives | Low | Medium | Review pattern specificity before deployment |
| Iteration calc is slow on large datasets | Medium | Low | Add batch processing, --limit option |
