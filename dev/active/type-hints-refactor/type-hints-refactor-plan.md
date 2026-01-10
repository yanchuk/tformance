# Type Hints & Code Refactoring Plan

**Last Updated:** 2026-01-10
**Status:** PLANNING
**Effort:** L (8-10 days) - Revised after plan review

## Executive Summary

Add comprehensive type hints to three critical service files (~3,000 lines total) while refactoring for simplicity. This improves AI coding agent effectiveness, IDE support, and catches bugs at development time. Includes pyright enforcement in pre-commit for future code.

### Target Files

| File | Lines | Functions | Current Type Coverage |
|------|-------|-----------|----------------------|
| `insight_llm.py` | 794 | 9 | ~60% (return types only) |
| `github_sync.py` | 1,138 | 17 | ~50% (partial annotations) |
| `llm_prompts.py` | 1,043 | 11 | ~40% (missing param types) |

## Current State Analysis

### Type Hint Status

**Existing Patterns (Good):**
- `TYPE_CHECKING` imports used to avoid circular imports
- Some functions have return type annotations
- `dataclass` used in `llm_prompts.py` (TimelineEvent)
- `TypedDict` patterns exist in other services (ai_detector.py, survey_service.py)

**Problems:**
1. **Untyped parameters**: Most functions lack parameter type hints
   ```python
   # Current - what is data?
   def build_metric_cards(data: dict) -> list[dict]:

   # Better - clear structure
   def build_metric_cards(data: InsightData) -> list[MetricCard]:
   ```

2. **Generic `dict` returns**: Functions return `dict` instead of `TypedDict`
   ```python
   def _convert_pr_to_dict(pr) -> dict:  # What keys? What types?
   ```

3. **Untyped library objects**: PyGithub objects passed as `Any`
   ```python
   def _convert_pr_to_dict(pr) -> dict:  # pr is PullRequest from PyGithub
   ```

4. **Missing generics**: List/dict without element types
   ```python
   def get_top_contributors(...) -> list[dict]:  # list of what?
   ```

### Refactoring Opportunities

**1. insight_llm.py (794 lines)**

| Issue | Location | Fix |
|-------|----------|-----|
| Large data dict | `gather_insight_data()` | Create `InsightData` TypedDict |
| Repeated card logic | `build_metric_cards()` | Extract `MetricCard` dataclass |
| Bot pattern list | Lines 334-346 | Move to constants module |
| JSON schema duplication | Lines 50-95 | Move to `prompts/schemas.py` |

**2. github_sync.py (1,138 lines)**

| Issue | Location | Fix |
|-------|----------|-----|
| Untyped PyGithub objects | Throughout | Add `github.PullRequest` types |
| Dict returns | `_convert_pr_to_dict()` | Create `PRDict` TypedDict |
| Complex sync functions | `_process_prs()` | Extract smaller typed helpers |
| Repeated rate limit handling | Multiple functions | Extract decorator/context manager |

**3. llm_prompts.py (1,043 lines)**

| Issue | Location | Fix |
|-------|----------|-----|
| 400-line hardcoded string | Lines 41-416 | Already has template source |
| Untyped timeline functions | `build_timeline()` | Better use of TimelineEvent |
| Complex context building | `build_llm_pr_context()` | Extract typed helper functions |

## Proposed Future State

### New Type Definitions

Create `apps/metrics/types.py`:

```python
from typing import TypedDict, Literal, Required, NotRequired

# === Metric Cards ===
class MetricCard(TypedDict):
    label: str
    value: str
    trend: Literal["positive", "negative", "neutral", "warning"]

# === Insight Response (from LLM) ===
class InsightAction(TypedDict):
    action_type: str
    label: str

class InsightResponse(TypedDict):
    headline: str
    detail: str
    recommendation: str
    actions: list[InsightAction]
    metric_cards: list[MetricCard]
    is_fallback: bool

# === Insight Data (input to LLM) ===
class ThroughputMetrics(TypedDict, total=False):
    current: int
    previous: int
    pct_change: float | None

class CycleTimeMetrics(TypedDict, total=False):
    current: float | None
    previous: float | None
    pct_change: float | None

class VelocityMetrics(TypedDict, total=False):
    throughput: ThroughputMetrics
    cycle_time: CycleTimeMetrics

class QualityMetrics(TypedDict, total=False):
    revert_count: int
    revert_rate: float
    hotfix_count: int
    avg_review_rounds: float
    large_pr_pct: float

class AIImpactMetrics(TypedDict, total=False):
    ai_pr_count: int
    non_ai_pr_count: int
    ai_adoption_pct: float
    ai_avg_cycle_time: float | None
    non_ai_avg_cycle_time: float | None
    cycle_time_difference_pct: float | None

class TeamHealthMetrics(TypedDict, total=False):
    active_contributors: int
    review_distribution: dict[str, float]
    bus_factor: int

class ContributorInfo(TypedDict):
    github_username: str
    display_name: str
    pr_count: int
    pct_share: float

class CopilotMetrics(TypedDict, total=False):
    total_suggestions: int
    total_acceptances: int
    acceptance_rate: float
    active_users: int
    total_seats: int

class InsightData(TypedDict):
    """Full data structure passed to insight generation."""
    velocity: Required[VelocityMetrics]
    quality: Required[QualityMetrics]
    ai_impact: Required[AIImpactMetrics]
    team_health: Required[TeamHealthMetrics]
    top_contributors: Required[list[ContributorInfo]]
    copilot_metrics: NotRequired[CopilotMetrics | None]
    jira_metrics: NotRequired[dict | None]
```

Create `apps/integrations/types.py`:

```python
from typing import TypedDict

class PRDict(TypedDict):
    id: int
    number: int
    title: str
    state: str
    merged: bool
    merged_at: str | None
    created_at: str
    updated_at: str
    additions: int
    deletions: int
    commits: int
    changed_files: int
    user: dict
    base: dict
    head: dict
    html_url: str
    jira_key: str

class SyncResult(TypedDict):
    prs_created: int
    prs_updated: int
    reviews_synced: int
    commits_synced: int
    errors: list[str]
```

### Pyright Configuration

Add to `pyproject.toml`:

```toml
[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "basic"
include = ["apps/"]
exclude = ["**/migrations", "**/tests", "dev/", "**/__pycache__"]

# Django-specific settings
reportMissingImports = true
reportMissingTypeStubs = false
reportUnusedImport = false              # Handled by ruff
reportPrivateUsage = false              # Django uses private attrs internally
reportUnknownMemberType = false         # Django QuerySets have dynamic types
reportUnknownArgumentType = false       # Factory Boy and Django have dynamic typing
reportGeneralTypeIssues = "warning"     # Start with warnings, not errors

# Allow untyped third-party libraries
useLibraryCodeForTypes = true
pythonPlatform = "Linux"                # Match production environment
```

Add to `.pre-commit-config.yaml`:

```yaml
  - repo: https://github.com/RobertCraigie/pyright-python
    rev: v1.1.391  # Pin to same version as pyproject.toml
    hooks:
      - id: pyright
        additional_dependencies: [pyright==1.1.391]
        args: ["--warnings"]  # Start with warnings only
```

**Note:** GitHub Actions CI integration deferred - will be added after local validation complete.

## Implementation Phases

### Phase 1: Setup & Types Foundation (Day 1)
- Add pyright to dev dependencies
- Create `apps/metrics/types.py` with core TypedDicts
- Create `apps/integrations/types.py` with sync types
- Configure pyright in `pyproject.toml`
- Add pyright hook to pre-commit (warnings mode)

### Phase 2: insight_llm.py (Days 2-3)
- Add TypedDict imports and parameter types
- Replace `dict` returns with typed alternatives
- Extract bot patterns to constants
- Move JSON schema to prompts/schemas.py
- Refactor `build_metric_cards()` with MetricCard
- Add explicit error types in exception handlers

### Phase 3: github_sync.py (Days 3-4)
- Add PyGithub type imports
- Create and apply PRDict TypedDict
- Type all function parameters
- Extract rate limit handling to decorator
- Simplify `_process_prs()` with typed helpers

### Phase 4: llm_prompts.py (Days 5-6)
- Apply existing TimelineEvent dataclass consistently
- Type all function parameters and returns
- Extract complex conditionals to typed helpers
- Ensure `build_llm_pr_context()` returns typed structure

### Phase 5: Verification & Enforcement (Day 7)
- Run pyright in strict mode on modified files
- Fix remaining type errors
- Update pre-commit to error mode (not just warnings)
- Update CLAUDE.md with typing guidelines
- Document typing patterns for future code

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes | Medium | TDD - run tests after each function |
| PyGithub stubs incomplete | Medium | Test pyright BEFORE starting; use specific `# type: ignore[code]` |
| Circular imports | Medium | Use `TYPE_CHECKING` pattern consistently |
| Over-typing (too complex) | Low | Start with basic mode, not strict |
| Slows down CI | Low | Pyright is fast (~5s for full codebase) |
| Type ignore proliferation | Medium | Pre-define acceptable ignore patterns; document in CLAUDE.md |
| Groq/LiteLLM stub gaps | Medium | Test early; these libraries may lack complete stubs |
| Factory Boy type issues | Medium | Factory Boy has incomplete stubs; may need ignores in tests |
| Django model dynamic types | Medium | Use `reportUnknownMemberType = false` in config |

### Type Ignore Documentation

Add to CLAUDE.md when complete:

```markdown
## Type Ignore Patterns

When pyright reports false positives, use specific error codes:

| Pattern | When to Use |
|---------|-------------|
| `# type: ignore[reportGeneralTypeIssues]` | Django QuerySet operations |
| `# type: ignore[reportArgumentType]` | Factory Boy dynamic kwargs |
| `# type: ignore[reportAttributeAccessIssue]` | Django model dynamic attrs |
| `# type: ignore[reportUnknownMemberType]` | Third-party library gaps |

**NEVER use bare `# type: ignore`** - always specify the error code.
```

## Success Metrics

1. **Type Coverage**: 90%+ on target files (measurable via pyright)
2. **Tests Pass**: All existing tests remain green
3. **Pyright Clean**: Zero errors in modified files
4. **No Runtime Impact**: No performance regression
5. **AI Agent Benefit**: Demonstrated improvement in code suggestions

## Dependencies

- `pyright` package (add to dev dependencies)
- Python 3.12 type features (`|` union syntax, etc.)
- PyGithub type stubs (bundled with package)

## TDD Workflow

For each file:
1. Run existing tests to establish baseline
2. Add types incrementally (function by function)
3. Run tests after each function
4. Run pyright to catch static errors
5. Refactor for simplicity while maintaining types
6. Final verification: tests + pyright + ruff
