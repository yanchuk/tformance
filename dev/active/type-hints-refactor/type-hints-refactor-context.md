# Type Hints & Code Refactoring - Context

**Last Updated:** 2026-01-10
**Status:** PLANNING

## Key Files

### Target Files (to modify)

| File | Lines | Functions | Purpose |
|------|-------|-----------|---------|
| `apps/metrics/services/insight_llm.py` | 794 | 9 | LLM insight generation |
| `apps/integrations/services/github_sync.py` | 1,138 | 17 | GitHub PR sync |
| `apps/metrics/services/llm_prompts.py` | 1,043 | 11 | LLM prompt building |

### Files to Create

| File | Purpose |
|------|---------|
| `apps/metrics/types.py` | TypedDict definitions for metrics |
| `apps/integrations/types.py` | TypedDict definitions for sync |

### Configuration Files

| File | Changes |
|------|---------|
| `pyproject.toml` | Add [tool.pyright] section |
| `.pre-commit-config.yaml` | Add pyright hook |

### Reference Files (existing patterns)

| File | Pattern |
|------|---------|
| `apps/metrics/services/ai_detector.py` | TypedDict examples |
| `apps/metrics/services/survey_service.py` | TypedDict examples |
| `apps/metrics/services/llm_prompts.py` | dataclass (TimelineEvent) |
| `apps/integrations/services/integration_flags.py` | dataclass pattern |

## Function Inventory

### insight_llm.py (9 functions)

```python
def resolve_action_url(action: dict, days: int) -> str:
def build_metric_cards(data: dict) -> list[dict]:
def _is_bot_username(username: str | None) -> bool:
def _get_top_contributors(team: Team, start_date: date, end_date: date, limit: int = 5) -> list[dict]:
def gather_insight_data(team: Team, start_date: date, end_date: date, days: int = 30) -> dict:
def build_insight_prompt(data: dict) -> str:
def _create_fallback_insight(data: dict) -> dict:
def generate_insight(data: dict, api_key: str | None = None, model: str | None = None) -> dict:
def cache_insight(team: Team, insight: dict, target_date: date, days: int = 30) -> DailyInsight:
```

**Typing Needs:**
- `data: dict` → `data: InsightData`
- `-> list[dict]` → `-> list[MetricCard]`
- `-> dict` → `-> InsightResponse`

### github_sync.py (17 functions)

```python
def _convert_pr_to_dict(pr) -> dict:                    # UNTYPED param
def get_repository_pull_requests(access_token, ...) -> Generator:
def get_updated_pull_requests(access_token, ...) -> Generator:
def get_pull_request_reviews(access_token, ...) -> list[dict]:
def _sync_pr_reviews(pr, access_token, ...) -> tuple[int, int]:
def sync_pr_commits(pr, access_token) -> int:
def sync_pr_check_runs(pr, access_token) -> int:
def sync_pr_files(pr, access_token) -> int:
def _process_prs(tracked_repo, access_token, ...) -> dict:
def sync_repository_history(tracked_repo) -> dict:
def sync_repository_incremental(tracked_repo) -> dict:
def sync_repository_deployments(tracked_repo) -> dict:
def _sync_pr_comments(pr, access_token) -> tuple[int, int]:
def sync_pr_issue_comments(pr, access_token) -> int:
def sync_pr_review_comments(pr, access_token) -> int:
def calculate_pr_iteration_metrics(pr) -> None:
def calculate_reviewer_correlations(team) -> int:
```

**Typing Needs:**
- PyGithub type imports: `from github import PullRequest as GHPullRequest`
- `pr` params → `pr: PullRequest` (Django model)
- `-> dict` → `-> SyncResult`
- Generator return types

### llm_prompts.py (11 functions)

```python
def calculate_relative_hours(timestamp: datetime | None, baseline: datetime | None) -> float | None:
def _format_timestamp_prefix(timestamp: datetime | None, baseline: datetime | None) -> str:
def _get_member_display_name(member) -> str:        # UNTYPED param
def get_user_prompt(pr: PullRequest, ...) -> str:
def build_llm_pr_context(pr: PullRequest) -> str:
def _get_repo_languages(pr: PullRequest) -> str:
def _collect_timeline_events(pr: PullRequest, ...) -> list[dict]:  # should be list[TimelineEvent]
def build_timeline(pr: PullRequest) -> list[TimelineEvent]:
def format_review_content(review):                  # nested, UNTYPED
def format_comment_content(comment):                # nested, UNTYPED
def format_timeline(events: list[TimelineEvent], max_events: int = 15) -> str:
```

**Typing Needs:**
- `member` param type (TeamMember)
- Consistent TimelineEvent usage
- Nested function types

## Key Decisions

### 1. TypedDict vs dataclass

**Use TypedDict for:**
- Data returned from functions (dict-like structure)
- Data passed to/from JSON serialization
- Backward compatibility with existing dict usage

**Use dataclass for:**
- Objects with behavior/methods
- Immutable configuration objects
- Complex nested structures

### 2. Strict vs Basic Mode

**Start with Basic Mode:**
- `typeCheckingMode = "basic"` in pyproject.toml
- Fix obvious issues first
- Move to strict after stabilization

### 3. Type Ignore Strategy

Use `# type: ignore[specific-error]` for:
- PyGithub stubs that are incomplete
- Django dynamic attributes
- Third-party library edge cases

**Never use bare `# type: ignore`** - always specify the error code.

### 4. Import Strategy

Use `TYPE_CHECKING` for:
- Django model imports (avoid circular imports)
- Heavy imports only used in annotations

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.metrics.models import PullRequest
    from apps.teams.models import Team
```

## Existing Type Patterns in Codebase

### ai_detector.py Pattern

```python
from typing import TypedDict

class AIReviewerResult(TypedDict):
    is_ai_reviewer: bool
    reviewer_type: str
    confidence: float

def analyze_reviewer(username: str) -> AIReviewerResult:
    ...
```

### survey_service.py Pattern

```python
class AccuracyStats(TypedDict):
    total_responses: int
    ai_correct: int
    ai_accuracy: float

def calculate_accuracy(team: Team) -> AccuracyStats:
    ...
```

### llm_prompts.py dataclass Pattern

```python
@dataclass
class TimelineEvent:
    timestamp: datetime
    event_type: str
    author: str
    content: str
    relative_hours: float | None = None
```

## Testing Strategy

### For Each Modified Function:

1. **Before typing**: Run related tests
2. **Add types**: Parameter and return annotations
3. **Run pyright**: Fix static errors
4. **Run tests**: Ensure behavior unchanged
5. **Refactor**: Simplify if possible
6. **Final check**: All tests + pyright clean

### Test Files to Monitor:

```
apps/metrics/tests/services/test_insight_llm.py
apps/integrations/tests/test_github_sync.py
apps/metrics/tests/services/test_llm_prompts.py
```

## Dependencies

### Python Packages

```toml
# Add to [dependency-groups] dev
"pyright>=1.1.350",
```

### Pre-commit Hook

```yaml
- repo: https://github.com/RobertCraiforthy/pyright-python
  rev: v1.1.350
  hooks:
    - id: pyright
      additional_dependencies: [pyright]
```

## External References

- [PyGithub Type Stubs](https://github.com/PyGithub/PyGithub) - Bundled
- [Django Stubs](https://github.com/typeddjango/django-stubs) - Not using, too strict
- [Pyright Documentation](https://microsoft.github.io/pyright/)
- [Python Typing Best Practices](https://typing.readthedocs.io/en/latest/guides/index.html)
