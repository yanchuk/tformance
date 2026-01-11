# Code Simplification & Complexity Reduction Plan

**Last Updated:** 2026-01-11

## Executive Summary

Comprehensive audit of the Tformance Django SaaS codebase identified **10 high-complexity files** totaling ~8,500 lines with significant refactoring opportunities. The code simplifier analysis reveals **~600+ lines of duplicated code** and several "god functions" exceeding 200 lines.

### Key Metrics

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Duplicated code lines | ~600+ | <100 | 83% reduction |
| Largest function | 280 lines | <50 lines | 82% reduction |
| Max parameters per function | 26 | <7 | 73% reduction |
| Files >500 lines | 8 | 4 | 50% reduction |

---

## Current State Analysis

### Complexity Hotspots (Ranked by Severity)

| Rank | File | Lines | Key Issues | Refactoring Potential |
|------|------|-------|------------|----------------------|
| 1 | `github_graphql.py` | 1,065 | **230 lines** duplicated retry logic across 5 methods | High - Extract `_execute_with_retry()` |
| 2 | `pr_list_service.py` | 612 | **280-line god function** with 20+ filter branches | High - Filter registry pattern |
| 3 | `github_sync.py` | 1,148 | N+1 patterns, mixed concerns, 6 processing passes | Medium - Extract to processors |
| 4 | `llm_prompts.py` | 722 | **26 parameters** in one function, duplicate patterns | High - PRContext TypedDict |
| 5 | `insight_llm.py` | 802 | God object with 7+ service dependencies | Medium - Extract data gathering |
| 6 | `groq_batch.py` | 812 | 3 response format versions, complex polling | Medium - Version adapter pattern |
| 7 | `sync_historical_data_task` | 273 | Single function, 13-param nested callback | Medium - Extract progress handler |
| 8 | `dashboard/pr_metrics.py` | 587 | Repeated aggregation patterns | Low - Query builder extraction |
| 9 | `copilot_metrics.py` | 650 | Dual code paths (mock vs real) | Low - Already feature-flagged |
| 10 | `aggregation_service.py` | 315 | Boolean flag complexity | Low - Minor refactor |

### Code Smell Categories

1. **DRY Violations** (~600 lines)
   - Retry logic copied 5x in `github_graphql.py`
   - Boolean filter pattern repeated 3x in `pr_list_service.py`
   - `_LazyPrompt` class duplicated across 2 files

2. **God Functions** (3 instances)
   - `get_prs_queryset()` - 280 lines, 20+ branches
   - `sync_historical_data_task()` - 273 lines
   - `_process_prs()` - 130 lines

3. **Parameter Explosion** (2 instances)
   - `get_user_prompt()` - 26 parameters
   - Progress callback - 13 parameters

4. **Magic Numbers** (~15 instances)
   - Timeout values, retry counts, thresholds

---

## Proposed Future State

### Architecture Improvements

```
BEFORE:                                    AFTER:
┌─────────────────────────┐               ┌─────────────────────────┐
│   github_graphql.py     │               │   github_graphql.py     │
│   (1,065 lines)         │               │   (800 lines)           │
│   - 5x retry logic      │      →        │   - 1x _execute_with_   │
│   - Magic numbers       │               │     retry() helper      │
│   - Inline imports      │               │   - Named constants     │
└─────────────────────────┘               └─────────────────────────┘

┌─────────────────────────┐               ┌─────────────────────────┐
│   pr_list_service.py    │               │   pr_list_service.py    │
│   (612 lines)           │               │   (250 lines)           │
│   - 280-line function   │      →        │   - Filter registry     │
│   - 20+ if branches     │               │   - Extracted handlers  │
│   - Loose typing        │               │   - Type-safe filters   │
└─────────────────────────┘               └─────────────────────────┘

┌─────────────────────────┐               ┌─────────────────────────┐
│   llm_prompts.py        │               │   llm_prompts.py        │
│   (722 lines)           │               │   (500 lines)           │
│   - 26 parameters       │      →        │   - PRContext TypedDict │
│   - Repeated patterns   │               │   - Extracted utilities │
└─────────────────────────┘               └─────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Quick Wins (P0) - Low Risk, High Impact
**Estimated Effort:** 4-6 hours
**Risk Level:** Low

Focus on `github_graphql.py` - the highest-impact, lowest-risk refactoring.

#### 1.1 Extract Retry Logic Helper
Extract the duplicated retry pattern into a single `_execute_with_retry()` method.

```python
async def _execute_with_retry(
    self,
    query,
    variables: dict,
    operation_name: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict:
    """Execute GraphQL query with retry logic and rate limit checking.

    Args:
        query: GraphQL query object
        variables: Variables to pass to the query
        operation_name: Human-readable name for logging
        max_retries: Maximum retry attempts on timeout

    Returns:
        dict: Query result

    Raises:
        GitHubGraphQLRateLimitError: When rate limit is exceeded
        GitHubGraphQLTimeoutError: After max_retries timeout failures
        GitHubGraphQLError: On other query failures
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            result = await self._execute(query, variable_values=variables)
            await self._check_rate_limit(result, operation_name)
            return result
        except GitHubGraphQLRateLimitError:
            raise
        except TimeoutError as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                logger.warning(
                    f"Timeout during {operation_name}, attempt {attempt + 1}/{max_retries}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                error_msg = f"GraphQL request timed out for {operation_name} after {max_retries} attempts"
                logger.error(error_msg)
                raise GitHubGraphQLTimeoutError(error_msg) from e
        except Exception as e:
            error_msg = f"GraphQL query failed for {operation_name}: {type(e).__name__}: {e}"
            logger.error(error_msg)
            raise GitHubGraphQLError(error_msg) from e

    raise GitHubGraphQLTimeoutError(
        f"GraphQL request timed out for {operation_name} after {max_retries} attempts"
    ) from last_error
```

#### 1.2 Add Named Constants

```python
# Add after existing imports, before class definition
RATE_LIMIT_THRESHOLD = 100
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_WAIT_SECONDS = 3600
GRAPHQL_RATE_LIMIT_POINTS = 5000
```

#### 1.3 Move Import to Module Level
Move `import asyncio` from inside methods to top of file.

#### 1.4 Simplify Fetch Methods
After extraction, each fetch method reduces from ~60-90 lines to ~15-25 lines.

**Example - Before:**
```python
async def fetch_prs_bulk(self, owner: str, repo: str, cursor: str | None = None, max_retries: int = 3) -> dict:
    # ~90 lines with retry logic
```

**Example - After:**
```python
async def fetch_prs_bulk(self, owner: str, repo: str, cursor: str | None = None, max_retries: int = DEFAULT_MAX_RETRIES) -> dict:
    """Fetch pull requests in bulk with pagination support."""
    result = await self._execute_with_retry(
        query=FETCH_PRS_BULK_QUERY,
        variables={"owner": owner, "repo": repo, "cursor": cursor},
        operation_name=f"fetch_prs_bulk({owner}/{repo})",
        max_retries=max_retries,
    )
    # ~15 lines for logging and return
    return result
```

---

### Phase 2: Structural Improvements (P1)
**Estimated Effort:** 8-12 hours
**Risk Level:** Medium

#### 2.1 Create PRContext TypedDict
**File:** `apps/metrics/types.py`

```python
from typing import TypedDict

class PRBasicInfo(TypedDict, total=False):
    """Basic PR identification and content."""
    title: str
    body: str
    number: int
    author: str
    github_repo: str

class PRCodeChanges(TypedDict, total=False):
    """Code change metrics."""
    additions: int
    deletions: int
    files_changed: int
    files: list[dict]  # File path, status, changes

class PRFlags(TypedDict, total=False):
    """Boolean status flags."""
    is_draft: bool
    is_revert: bool
    is_hotfix: bool
    has_jira: bool

class PRTimingMetrics(TypedDict, total=False):
    """Timing and lifecycle metrics."""
    created_at: str
    merged_at: str | None
    closed_at: str | None
    cycle_time_hours: float | None
    review_time_hours: float | None

class PRCollaboration(TypedDict, total=False):
    """Review and collaboration data."""
    reviews: list[dict]
    comments: list[dict]
    commits: list[dict]
    reviewers: list[str]

class PRContext(TypedDict, total=False):
    """Complete PR context for LLM prompts.

    Replaces 26 individual parameters with a structured type.
    """
    basic: PRBasicInfo
    code: PRCodeChanges
    flags: PRFlags
    timing: PRTimingMetrics
    collaboration: PRCollaboration
    # Legacy flat fields for backward compatibility
    title: str
    body: str
    # ... other fields
```

#### 2.2 Add get_user_prompt_v2()
**File:** `apps/metrics/services/llm_prompts.py`

```python
import warnings

def get_user_prompt_v2(context: PRContext) -> str:
    """Build user prompt from PR context.

    New API using structured PRContext instead of 26 parameters.
    """
    # Extract from structured context
    basic = context.get("basic", {})
    code = context.get("code", {})
    timing = context.get("timing", {})
    collaboration = context.get("collaboration", {})

    # Build prompt sections
    # ...

def get_user_prompt(
    # ... existing 26 parameters
) -> str:
    """Build user prompt from individual parameters.

    .. deprecated:: 2.0
        Use :func:`get_user_prompt_v2` with :class:`PRContext` instead.
    """
    warnings.warn(
        "get_user_prompt() is deprecated, use get_user_prompt_v2() with PRContext",
        DeprecationWarning,
        stacklevel=2
    )
    # Existing implementation
```

#### 2.3 Extract Filter Functions from pr_list_service.py

**File:** `apps/metrics/services/pr_filters.py` (new file)

```python
"""PR filter utilities for pr_list_service.

Extracted from pr_list_service.py to reduce complexity.
Each filter function is independently testable.
"""
from datetime import date
from django.db.models import Q, QuerySet, F, Avg

def apply_date_range_filter(
    qs: QuerySet,
    state_filter: str | None,
    date_from: date | None,
    date_to: date | None,
) -> QuerySet:
    """Apply date range filter with state-aware field selection.

    Date field logic:
    - Open PRs: Filter by pr_created_at
    - Merged/Closed PRs: Filter by merged_at
    - All states: OR query combining both logics
    """
    if not date_from and not date_to:
        return qs

    if state_filter == "open":
        return _filter_by_date_field(qs, "pr_created_at", date_from, date_to)

    if state_filter in ("merged", "closed"):
        return _filter_by_date_field(qs, "merged_at", date_from, date_to)

    # All states: combine with OR
    return _filter_all_states_date_range(qs, date_from, date_to)


def _filter_by_date_field(
    qs: QuerySet, field: str, date_from: date | None, date_to: date | None
) -> QuerySet:
    """Apply date range filter on a specific field."""
    if date_from:
        qs = qs.filter(**{f"{field}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{field}__date__lte": date_to})
    return qs


def _filter_all_states_date_range(
    qs: QuerySet, date_from: date | None, date_to: date | None
) -> QuerySet:
    """Apply date range for all states using appropriate fields."""
    open_q = Q(state="open")
    merged_q = Q(state__in=["merged", "closed"])

    if date_from:
        open_q &= Q(pr_created_at__date__gte=date_from)
        merged_q &= Q(merged_at__date__gte=date_from)
    if date_to:
        open_q &= Q(pr_created_at__date__lte=date_to)
        merged_q &= Q(merged_at__date__lte=date_to)

    return qs.filter(open_q | merged_q)


def apply_issue_type_filter(qs: QuerySet, issue_type: str | None) -> QuerySet:
    """Apply issue type filter with priority-based exclusions.

    Priority (highest to lowest):
    1. revert
    2. hotfix
    3. long_cycle
    4. large_pr
    5. missing_jira
    """
    if not issue_type:
        return qs

    handlers = {
        "revert": _filter_revert,
        "hotfix": _filter_hotfix,
        "long_cycle": _filter_long_cycle,
        "large_pr": _filter_large_pr,
        "missing_jira": _filter_missing_jira,
    }

    handler = handlers.get(issue_type)
    if handler:
        return handler(qs)
    return qs


def _filter_revert(qs: QuerySet) -> QuerySet:
    return qs.filter(is_revert=True)


def _filter_hotfix(qs: QuerySet) -> QuerySet:
    return qs.filter(is_hotfix=True, is_revert=False)


def _filter_long_cycle(qs: QuerySet) -> QuerySet:
    # Calculate threshold dynamically
    avg_result = qs.filter(cycle_time_hours__isnull=False).aggregate(
        avg_cycle=Avg("cycle_time_hours")
    )
    team_avg = avg_result["avg_cycle"] or 0
    threshold = float(team_avg) * 2 if team_avg else float("inf")

    return qs.filter(
        cycle_time_hours__gt=threshold,
        is_revert=False,
        is_hotfix=False,
    )


def _filter_large_pr(qs: QuerySet) -> QuerySet:
    # Similar pattern with exclusions
    pass


def _filter_missing_jira(qs: QuerySet) -> QuerySet:
    # Similar pattern with exclusions
    pass
```

---

### Phase 3: Major Refactoring (P2)
**Estimated Effort:** 12-16 hours
**Risk Level:** High

#### 3.1 Split github_sync.py into Module

```
apps/integrations/services/
├── github_sync/
│   ├── __init__.py          # Re-exports for backward compatibility
│   ├── sync.py               # Main sync orchestration
│   ├── processors.py         # PRProcessor, ReviewProcessor, etc.
│   ├── rate_limit.py         # Rate limit handling
│   └── metrics.py            # Iteration metrics calculation
├── github_sync.py            # Deprecated, imports from github_sync/
```

#### 3.2 Extract InsightDataGatherer

**File:** `apps/metrics/services/insight_data.py` (new file)

```python
"""Insight data gathering service.

Extracts data aggregation from insight_llm.py to reduce coupling.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.teams.models import Team

from apps.metrics.services.dashboard.pr_metrics import (
    get_pr_throughput,
    get_pr_velocity,
    get_pr_quality_metrics,
)
# ... other imports

@dataclass
class InsightData:
    """Aggregated data for insight generation."""
    velocity: dict
    quality: dict
    team_health: dict
    ai_impact: dict
    jira_metrics: dict | None
    copilot_metrics: dict | None


class InsightDataGatherer:
    """Gathers metrics from multiple sources for insight generation."""

    def __init__(self, team: "Team"):
        self.team = team

    def gather(self, start_date, end_date) -> InsightData:
        """Gather all metrics for the date range."""
        return InsightData(
            velocity=self._get_velocity_metrics(start_date, end_date),
            quality=self._get_quality_metrics(start_date, end_date),
            team_health=self._get_health_metrics(start_date, end_date),
            ai_impact=self._get_ai_metrics(start_date, end_date),
            jira_metrics=self._get_jira_metrics(start_date, end_date),
            copilot_metrics=self._get_copilot_metrics(start_date, end_date),
        )

    def _get_velocity_metrics(self, start_date, end_date) -> dict:
        return get_pr_velocity(self.team, start_date, end_date)

    # ... other _get_* methods
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing tests | Medium | High | Run full test suite before/after each change |
| Introducing regressions | Low | High | Refactor in small, testable increments |
| Performance degradation | Low | Medium | Profile critical paths before/after |
| Breaking API compatibility | Medium | Medium | Add deprecation warnings, keep old signatures |
| Incomplete refactoring | Medium | Low | Document TODO items, track in tasks file |

---

## Success Metrics

| Metric | Current | Phase 1 Target | Phase 2 Target | Phase 3 Target |
|--------|---------|----------------|----------------|----------------|
| Lines of duplicated code | ~600 | ~370 | ~170 | <100 |
| Max function length | 280 | 280 | <100 | <50 |
| Max params per function | 26 | 26 | <10 | <7 |
| Test coverage (services) | ~75% | ~75% | ~80% | ~85% |
| All tests passing | Yes | Yes | Yes | Yes |

---

## Verification Commands

```bash
# Before any refactoring - establish baseline
make test

# After each phase
make test ARGS='apps.integrations.tests'
make test ARGS='apps.metrics.tests'
make lint-team-isolation

# Check for regressions
.venv/bin/pytest --lf  # Run last failed tests
.venv/bin/pytest -x    # Stop on first failure

# Verify no type errors introduced
.venv/bin/pyright apps/integrations/services/github_graphql.py
.venv/bin/pyright apps/metrics/services/pr_list_service.py
```

---

## Dependencies

### External Dependencies
- None - all refactoring is internal

### Internal Dependencies
- Phase 2 depends on Phase 1 completion
- Phase 3 depends on Phase 2 completion

### Required Knowledge
- Python async/await patterns
- Django ORM QuerySet API
- TypedDict and type annotations
- Unit testing with pytest/Django TestCase
