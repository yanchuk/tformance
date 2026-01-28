# Jira Integration Enhancement Plan

## Overview

Enhance the existing Jira integration to provide full data flow from Jira tickets through PR enrichment to LLM insights and dashboards.

## Development Setup

**Work in isolated environment:**
- Create new git worktree: `git worktree add ../tformance-jira-enhancement feature/jira-integration-enhancement`
- All work done in separate branch: `feature/jira-integration-enhancement`
- Keep main branch clean for other work
- Merge via PR after testing complete

## Decisions Made

| Decision | Choice |
|----------|--------|
| Jira data fetch timing | Daily sync (existing pattern) |
| Story points field | Default `10016`, user override in team settings |
| PR-Jira relationship | Keep string-based (`jira_key` match) |
| LLM context | Core + description (summary, SP, priority, labels, status, description) |
| Jira key extraction | Title + branch only (body too unreliable - mentions vs links) |
| Changelog | Include - time-in-status tracking |
| Dashboards | Overview, Team, Performance, PR Detail |
| Feature gating | Check flag + integration exists + data synced |
| Token budget | Dynamic - add extra tokens when Jira context included |
| Sprints | Deferred - complex (boards vs projects), separate feature later |

---

## Strategic Context: Jira Enrichment (Not Separate Widgets)

### Positioning
**Primary:** Understand your team's velocity
**Secondary:** See if AI tools help

Jira data ENRICHES existing metrics rather than creating separate widgets.

### CTO Concerns Matrix

| Category | CTO Question | Jira Enrichment |
|----------|--------------|-----------------|
| **Velocity** | "Are we getting faster?" | Normalize by SP: "24h/SP cycle time" |
| **Performance** | "Who's delivering value?" | Per-developer SP: "Sarah: 21 SP (avg: 15)" |
| **Health** | "Is process working?" | Linkage rate, estimation accuracy |
| **Bottlenecks** | "Where does work get stuck?" | Time-in-status: "Review: 18h (55%)" |
| **Blockers** | "What's stopping us?" | Stuck high-priority tickets |
| **Quality** | "Are we shipping bugs?" | Bug rate by SP, revert correlation |

### AI Lens (Applied to All Above)
For each metric, add AI comparison:
- "AI PRs: 24h/SP vs Non-AI: 32h/SP"
- "AI best on bugs (65% faster), needs work on features"

### Planned SP Approach
Use historical baseline: "47 SP (↑12% vs 4-week avg: 42 SP)"
No sprint integration needed.

### Competitor Analysis
- **Jellyfish:** Correlates Git + Jira signals (no separate dashboards)
- **Swarmia:** Issue cycle time alongside PR metrics
- **LinearB:** Flags PRs missing Jira data, correlation focus
- **GetDX (Atlassian):** DORA + SPACE + surveys, $1B acquisition

### Dashboard Enrichment Examples

**Overview:**
```
VELOCITY: 47 SP delivered (↑12% vs avg) | 24h/SP cycle time
AI IMPACT: AI 28 SP, Non-AI 19 SP | AI best on bugs
HEALTH: 78% linkage | Estimation: 85% accurate
⚠️ BOTTLENECK: Code Review 18h (55% of cycle time)
```

**Team View:**
```
Developer | SP Delivered | Cycle/SP | AI Usage
Sarah     | 21 SP        | 4.2h ✓   | 80%
Alex      | 18 SP        | 5.1h     | 45%
Jordan    | 8 SP         | 8.0h ⚠️  | 20%
```

**Quality:**
```
Bug rate: 12% (healthy)
Reverts by SP: 1-3 SP: 1.2% | 13+ SP: 6.1% ⚠️
AI quality: 8% bugs vs Non-AI 11%
```

---

## Implementation Tasks

### 1. Model Updates - JiraIssue Enhancement

**File:** `apps/metrics/models/jira.py`

Add new fields:
```python
# Time-in-status from changelog (e.g., {"In Progress": 12.5, "Code Review": 18.0})
time_in_status = models.JSONField(default=dict)
status_transitions = models.IntegerField(default=0)  # Rework indicator
```

**Migration required:** Yes

---

### 2. Team Settings - Story Points Field Override

**File:** `apps/integrations/models/jira.py`

Add to `JiraIntegration`:
```python
story_points_field = models.CharField(
    max_length=50,
    default="customfield_10016",
    help_text="Jira custom field ID for story points"
)
```

**Migration required:** Yes

---

### 3. Jira Sync Enhancement

**File:** `apps/integrations/services/jira_client.py`

Changes:
- Add `expand="changelog"` to API call
- Use configurable story points field ID
- Parse changelog to calculate time-in-status

**File:** `apps/integrations/services/jira_sync.py`

Changes:
- Add changelog parsing logic
- Calculate `time_in_status` dict
- Calculate `status_transitions` count
- Add 429 retry logic with exponential backoff

Example changelog parsing:
```python
def _parse_changelog_to_time_in_status(changelog: dict, current_status: str) -> tuple[dict, int]:
    """Parse Jira changelog to calculate time spent in each status.

    Args:
        changelog: Jira changelog response
        current_status: Issue's current status (for calculating time since last transition)

    Returns:
        Tuple of (time_in_status dict, status_transitions count)
        Example: ({"In Progress": 12.5, "Code Review": 18.0}, 4)
    """
    time_in_status = defaultdict(float)
    transitions = 0

    # Extract only status field changes
    status_changes = []
    for history in changelog.get("histories", []):
        for item in history.get("items", []):
            if item.get("field") == "status":
                status_changes.append({
                    "timestamp": parse_datetime(history["created"]),
                    "from_status": item.get("fromString"),
                    "to_status": item.get("toString"),
                })
                transitions += 1

    # Sort by timestamp and calculate durations
    status_changes.sort(key=lambda x: x["timestamp"])

    for i, change in enumerate(status_changes):
        from_status = change["from_status"]
        if from_status and i > 0:
            duration = (change["timestamp"] - status_changes[i-1]["timestamp"]).total_seconds() / 3600
            time_in_status[from_status] += duration

    # Add time in current status (from last change to now)
    if status_changes:
        last_change = status_changes[-1]
        hours_in_current = (timezone.now() - last_change["timestamp"]).total_seconds() / 3600
        time_in_status[current_status] += hours_in_current

    return dict(time_in_status), transitions
```

---

### 4. Jira Key Extraction - Verify Current Implementation

**Current behavior:** Already extracts from title and branch (see `extract_jira_key()` in `jira_utils.py`)

**Decision:** Keep title + branch only. Body is too unreliable (mentions vs actual links).

**Verify in:** `apps/integrations/services/github_sync/converters.py`

Ensure PR conversion uses existing `extract_jira_key()` on title and branch only.

---

### 5. LLM Prompt Enhancement - PR Analysis

⚠️ **Use `/prompt-engineer` skill when implementing this task**
- Follow prompt engineering best practices
- Test prompt changes with real PR data before finalizing
- Bump `PROMPT_VERSION` after changes

**File:** `apps/metrics/prompts/render.py`

Add new parameters to `render_pr_user_prompt()`:
```python
jira_summary: str | None = None,
jira_description: str | None = None,
jira_story_points: float | None = None,
jira_priority: str | None = None,
jira_labels: list[str] | None = None,
jira_status: str | None = None,
jira_time_in_status: dict | None = None,
```

**File:** `apps/metrics/prompts/templates/pr_analysis/user.jinja2`

Add Jira context section:
```jinja2
{%- if jira_summary -%}
## Linked Jira Ticket: {{ jira_key }}
- Summary: {{ jira_summary }}
{%- if jira_description %}
- Description: {{ jira_description[:500] }}{% if jira_description|length > 500 %}...{% endif %}
{%- endif %}
{%- if jira_story_points %}
- Story Points: {{ jira_story_points }}
{%- endif %}
{%- if jira_priority %}
- Priority: {{ jira_priority }}
{%- endif %}
{%- if jira_labels %}
- Labels: {{ jira_labels|join(", ") }}
{%- endif %}
{%- if jira_status %}
- Status: {{ jira_status }}
{%- endif %}
{%- if jira_time_in_status %}
- Time in Status: {% for status, hours in jira_time_in_status.items() %}{{ status }}: {{ "%.1f"|format(hours) }}h{% if not loop.last %}, {% endif %}{% endfor %}
{%- endif %}
{%- endif %}
```

---

### 6. LLM Processing - Fetch Jira Data

**File:** `apps/metrics/services/llm_analyzer.py` (or wherever PR analysis is triggered)

Add helper to fetch Jira data for PR:
```python
def _get_jira_context_for_pr(pr: PullRequest) -> dict | None:
    """Fetch Jira ticket data for PR enrichment."""
    if not pr.jira_key:
        return None

    try:
        jira_issue = JiraIssue.objects.get(team=pr.team, jira_key=pr.jira_key)
        return {
            "jira_summary": jira_issue.summary,
            "jira_description": jira_issue.description,
            "jira_story_points": jira_issue.story_points,
            "jira_priority": jira_issue.priority,
            "jira_labels": jira_issue.labels,
            "jira_status": jira_issue.status,
            "jira_time_in_status": jira_issue.time_in_status,
        }
    except JiraIssue.DoesNotExist:
        return None
```

---

### 7. LLM Insights Enhancement

⚠️ **Use `/prompt-engineer` skill when implementing this task**
- Existing template has `{% if jira %}` section (lines 103-117) - extend it
- Follow prompt engineering best practices
- Bump `PROMPT_VERSION` after changes

**File:** `apps/metrics/prompts/templates/insight/user.jinja2`

Add Jira metrics section (conditional on data availability):
```jinja2
{%- if jira_metrics %}
## Jira Delivery Metrics
- Story Points Completed: {{ jira_metrics.story_points_completed }}
- Issues Resolved: {{ jira_metrics.issues_resolved }}
- Avg Cycle Time: {{ jira_metrics.avg_cycle_time_hours }}h
- PR-Jira Linkage Rate: {{ jira_metrics.linkage_rate }}%
{%- if jira_metrics.bottleneck_status %}
- Bottleneck: {{ jira_metrics.bottleneck_status }} ({{ jira_metrics.bottleneck_hours }}h avg)
{%- endif %}
{%- endif %}
```

**File:** `apps/insights/services/insight_data.py` (or equivalent)

Add Jira metrics collection:
```python
def _get_jira_metrics_for_insight(team, start_date, end_date) -> dict | None:
    """Collect Jira metrics for team insight if available."""
    if not _should_include_jira(team):
        return None

    sprint_metrics = get_jira_sprint_metrics(team, start_date, end_date)
    correlation = get_pr_jira_correlation(team, start_date, end_date)

    # Calculate bottleneck from time_in_status aggregation
    bottleneck = _find_status_bottleneck(team, start_date, end_date)

    return {
        "story_points_completed": sprint_metrics["story_points_completed"],
        "issues_resolved": sprint_metrics["issues_resolved"],
        "avg_cycle_time_hours": sprint_metrics["avg_cycle_time_hours"],
        "linkage_rate": correlation["linkage_rate"],
        "bottleneck_status": bottleneck.get("status"),
        "bottleneck_hours": bottleneck.get("avg_hours"),
    }
```

---

### 8. Feature Flag & Gating Logic

**File:** `apps/integrations/services/jira_utils.py`

Add gating helper:
```python
def should_include_jira_context(team) -> bool:
    """Check if Jira data should be included for this team."""
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

---

### 9. Dashboard Enrichment (Not Separate Widgets)

Jira data enriches existing metrics rather than creating new sections.

#### 9.1 Overview Dashboard Enrichment

**File:** `apps/dashboard/views/overview.py`

Enrich existing metrics:
- Velocity: Add "per SP" normalization → "47 SP delivered (↑12% vs avg)"
- AI Impact: Add SP breakdown → "AI PRs: 28 SP, Non-AI: 19 SP"
- Add Health row: "78% PR-Jira linkage"
- Add Bottleneck alert: "Review: 18h avg (⚠️ ↑40%)"

**Data Quality Indicator (Linkage Rate):**

Show linkage rate prominently so users understand data accuracy:

```
┌─────────────────────────────────────────────────────┐
│ 📊 Jira Data Coverage: 78% of PRs linked           │
│ ████████████████████░░░░░  78/100 PRs              │
│                                                     │
│ ✓ Good coverage - Jira metrics are representative │
└─────────────────────────────────────────────────────┘
```

**Linkage Thresholds:**
| Rate | Indicator | Message |
|------|-----------|---------|
| ≥70% | ✓ Green | "Good coverage - metrics representative" |
| 50-69% | ⚠️ Yellow | "Partial coverage - some PRs missing Jira links" |
| <50% | 🔴 Red | "Low coverage - Jira metrics may not be representative" |

**Caveat on SP-based metrics:**
When linkage < 70%, show caveat: "Based on 45% of PRs with Jira links"

#### 9.2 Team Analytics Enrichment

**File:** `apps/dashboard/views/team.py`

Enrich per-developer table:
- Add "SP Delivered" column
- Add "Cycle Time/SP" normalized metric
- Add linkage rate per developer
- Flag outliers (low linkage, high cycle/SP)

#### 9.3 Performance/Trends Enrichment

**File:** `apps/dashboard/views/performance.py`

Enrich existing trend charts:
- Throughput trend: Add SP delivered line alongside PR count
- Cycle time trend: Segment by issue type (Bug/Feature/Tech Debt)
- Add Quality section: Bug rate trend, revert rate by SP bucket
- Add Estimation accuracy: SP bucket vs actual cycle time

#### 9.4 PR Detail View Enrichment

**File:** `apps/pullrequests/views.py` (or equivalent)

Add linked Jira context card:
- Summary, status, priority, story points
- Time-in-status breakdown
- Expectation: "5 SP → expected 16h, actual 18h ✓"

---

### 10. Onboarding Integration & Sync Status

#### 10.1 Sync Status UI Enhancement

**File:** `templates/onboarding/sync_progress.html`

Add Jira sync phase to the status display (lines 724-732):
```javascript
// Current phases (GitHub only)
syncing_members → "Syncing team members"
syncing → "Importing PRs from last 30 days"
llm_processing → "Analyzing PRs with AI"

// NEW: Add Jira phases
syncing_jira → "Syncing Jira issues"
syncing_jira_phase2 → "Syncing older Jira issues (31-60 days)"
```

**File:** `apps/onboarding/views/github.py` - `sync_status()` endpoint

Add Jira sync status to JSON response:
```python
{
    # Existing fields...
    "jira_sync_status": "pending|syncing|completed|not_connected",
    "jira_issues_synced": count,
    "jira_sync_phase": "phase1|phase2|complete",
}
```

#### 10.2 Jira Historical Sync - Two-Phase Approach

**File:** `apps/integrations/_task_modules/jira_sync.py`

Add phased sync similar to GitHub:
```python
def sync_jira_project_task(project_id: int, days_back: int = 30, skip_recent: int = 0):
    """Sync Jira issues with configurable date range.

    Phase 1: days_back=30, skip_recent=0 → last 30 days
    Phase 2: days_back=60, skip_recent=30 → days 31-60
    """
```

**File:** `apps/integrations/services/jira_client.py`

Update JQL to filter by date:
```python
def get_project_issues(credential, project_key: str, days_back: int = 30, skip_recent: int = 0):
    """Fetch issues updated within date range."""
    if skip_recent > 0:
        # Phase 2: Skip recent days already synced
        jql = f"project = {project_key} AND updated >= -{days_back}d AND updated < -{skip_recent}d"
    else:
        # Phase 1: Recent issues only
        jql = f"project = {project_key} AND updated >= -{days_back}d"
```

#### 10.3 Celery Task Ordering

**Current flow (GitHub only):**
```
sync_github_members → sync_historical_data (30d) → llm_processing → metrics → insights
```

**New flow (with Jira):**
```
sync_github_members
    ↓
sync_historical_data (30d)  ←─┐
    ↓                          │ Parallel if Jira connected
sync_jira_issues (30d)     ←─┘
    ↓
llm_processing (with Jira context now available)
    ↓
metrics → insights
```

**File:** `apps/integrations/onboarding_pipeline.py`

Update Phase 1 pipeline to include Jira:
```python
def start_phase1_pipeline(team_id: int, repo_ids: list[int], jira_project_ids: list[int] | None = None):
    """Start onboarding pipeline with optional Jira sync.

    If Jira connected, sync Jira issues BEFORE LLM processing
    so Jira context is available for PR analysis.
    """
    # ... existing GitHub sync ...

    # NEW: If Jira connected, sync before LLM
    if jira_project_ids:
        team.onboarding_pipeline_status = "syncing_jira"
        team.save(update_fields=["onboarding_pipeline_status"])
        sync_jira_projects_onboarding.delay(team_id, jira_project_ids, days_back=30)

    # Then continue to LLM processing...
```

**Phase 2 chain update:**
```python
chain(
    # ... existing GitHub Phase 2 ...
    sync_historical_data_task.si(team_id, repo_ids, days_back=90, skip_recent=30),

    # NEW: Jira Phase 2 (if connected)
    sync_jira_historical_task.si(team_id, days_back=60, skip_recent=30),

    # Continue with LLM, metrics...
)
```

#### 10.4 Jira Sync Timing Decision

| Timing | Pros | Cons |
|--------|------|------|
| **During onboarding (if connected)** | User sees Jira data immediately | Longer onboarding wait |
| **After GitHub completes** | Faster initial dashboard | Jira context missing from first LLM run |
| **Parallel with GitHub** | Optimal speed | Complex error handling |

**Recommendation:** Sync Jira **after GitHub PRs but before LLM processing** so:
1. PR-Jira matching has both datasets
2. LLM analysis includes Jira context from the start
3. User doesn't wait for Jira during initial PR sync

---

### 11. Retry Logic for API Errors

**File:** `apps/integrations/services/jira_client.py`

Add retry decorator:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import HTTPError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(HTTPError),
)
def get_project_issues(credential, project_key: str, since: datetime | None = None):
    # existing implementation
```

---

### 11. Dynamic Token Budget Based on Jira Context

**File:** `apps/metrics/prompts/constants.py`

Add token budget constants:
```python
# Base token budgets
PR_ANALYSIS_BASE_TOKENS = 4000
INSIGHT_BASE_TOKENS = 6000

# Additional tokens when Jira context is available
JIRA_CONTEXT_ADDITIONAL_TOKENS = 500
```

**File:** `apps/metrics/services/llm_analyzer.py` (or wherever LLM calls are made)

Add dynamic budget calculation:
```python
from apps.metrics.prompts.constants import (
    PR_ANALYSIS_BASE_TOKENS,
    INSIGHT_BASE_TOKENS,
    JIRA_CONTEXT_ADDITIONAL_TOKENS,
)
from apps.integrations.services.jira_utils import should_include_jira_context

def get_token_budget(team, prompt_type: str) -> int:
    """Calculate token budget dynamically based on context availability.

    Args:
        team: Team instance
        prompt_type: Either "pr_analysis" or "insight"

    Returns:
        Token budget (base + Jira bonus if applicable)
    """
    base_tokens = {
        "pr_analysis": PR_ANALYSIS_BASE_TOKENS,
        "insight": INSIGHT_BASE_TOKENS,
    }.get(prompt_type, PR_ANALYSIS_BASE_TOKENS)

    # Add extra tokens if Jira context will be included
    if should_include_jira_context(team):
        return base_tokens + JIRA_CONTEXT_ADDITIONAL_TOKENS

    return base_tokens
```

**Usage in LLM calls:**
```python
# Before
response = llm_client.complete(
    messages=messages,
    max_tokens=4000,  # Hardcoded
)

# After
response = llm_client.complete(
    messages=messages,
    max_tokens=get_token_budget(team, "pr_analysis"),  # Dynamic
)
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `apps/metrics/models/jira.py` | Add `time_in_status`, `status_transitions` fields |
| `apps/integrations/models/jira.py` | Add `story_points_field` to JiraIntegration |
| `apps/integrations/services/jira_client.py` | Add changelog expansion, configurable SP field, retry logic |
| `apps/integrations/services/jira_sync.py` | Add changelog parsing, time-in-status calculation |
| `apps/integrations/services/jira_utils.py` | Add `should_include_jira_context()` |
| `apps/integrations/services/github_sync/converters.py` | Verify Jira key extraction (title + branch only) |
| `apps/integrations/onboarding_pipeline.py` | Add Jira sync phases, task ordering |
| `apps/integrations/_task_modules/jira_sync.py` | Add phased sync (30d/60d) |
| `templates/onboarding/sync_progress.html` | Add Jira sync phase labels |
| `apps/onboarding/views/github.py` | Add Jira status to `sync_status()` response |
| `apps/metrics/prompts/render.py` | Add Jira context parameters |
| `apps/metrics/prompts/templates/pr_analysis/user.jinja2` | Add Jira ticket section |
| `apps/metrics/prompts/templates/insight/user.jinja2` | Add Jira metrics section |
| `apps/metrics/services/llm_analyzer.py` | Fetch Jira data for PR analysis |
| `apps/insights/services/` | Add Jira metrics collection |
| `apps/dashboard/views/` | Enrich existing views with Jira data |

---

## Testing Strategy

### Mock Data Scenarios - Team Configurations

| Scenario | Team Setup | Purpose |
|----------|------------|---------|
| **Team A** | Full Jira: all PRs linked, good SP data | Happy path - all metrics work |
| **Team B** | Sparse linkage (30% PRs linked) | Partial data, linkage rate calculations |
| **Team C** | No Jira integration | Feature gating, graceful degradation |
| **Team D** | Jira connected, no issues synced yet | Edge case - integration exists but empty |
| **Team E** | Custom SP field (not 10016) | Story points field override |
| **Team F** | Jira connected, feature flag OFF | Flag gating works correctly |

### Edge Cases to Test

#### Jira Key Extraction
| Case | Input | Expected |
|------|-------|----------|
| Key in title only | `title="PROJ-123 Fix bug"` | `jira_key="PROJ-123"` |
| Key in branch only | `branch="feature/PROJ-456-add-login"` | `jira_key="PROJ-456"` |
| Key in both (same) | `title="PROJ-123"`, `branch="PROJ-123-fix"` | `jira_key="PROJ-123"` |
| Key in both (different) | `title="PROJ-123"`, `branch="PROJ-456"` | First match wins (title) |
| No key anywhere | `title="Fix bug"`, `branch="feature/login"` | `jira_key=""` |
| Malformed keys | `proj-123` (lowercase), `PROJ123` (no dash) | `jira_key=""` |
| Key in body (ignored) | `body="Related to PROJ-789"` | Body not parsed |

#### Story Points
| Case | Value | Expected Behavior |
|------|-------|-------------------|
| Normal SP | `5.0` | Store and use in calculations |
| Null SP | `None` | Skip in SP-related metrics, don't break |
| Zero SP | `0` | Include but flag as anomaly |
| Decimal SP | `0.5`, `2.5` | Handle decimal math correctly |
| Very high SP | `100+` | Include but may flag as outlier |
| Wrong field configured | Field returns `None` | Log warning, continue without SP |

#### Time-in-Status (Changelog)
| Case | Scenario | Expected |
|------|----------|----------|
| No transitions | Issue created → Done immediately | `time_in_status = {}` or single status |
| Normal flow | Open → In Progress → Review → Done | `{"In Progress": 8.0, "Review": 4.0}` |
| Circular transitions | In Progress → Review → In Progress → Done | Accumulate time per status |
| Reopened issues | Done → Open → In Progress → Done | Track all time, multiple Done entries |
| Very long status | 1000+ hours in one status | Handle large numbers |
| Empty changelog | No history records | `time_in_status = {}`, `status_transitions = 0` |

#### API/Sync Edge Cases
| Case | Scenario | Expected Behavior |
|------|----------|-------------------|
| 429 Rate Limit | Jira returns 429 | Retry with exponential backoff (3 attempts) |
| API Timeout | Request times out | Log error, continue with other projects |
| Deleted Issue | Issue no longer exists | Skip gracefully, log warning |
| No matching user | Jira user email not in TeamMember | `assignee = None`, issue still synced |
| Long description | 5000+ chars | Truncate to 500 in LLM context |
| Unicode/emoji | Summary: "🚀 Fix 日本語 bug" | Handle correctly in all paths |

#### Feature Gating
| Case | Conditions | `should_include_jira_context()` |
|------|------------|--------------------------------|
| All enabled | Flag ON, integration exists, issues synced | `True` |
| Flag off | Flag OFF, integration exists, issues synced | `False` |
| No integration | Flag ON, no JiraIntegration | `False` |
| No data yet | Flag ON, integration exists, no JiraIssue | `False` |

#### Linkage Rate & Data Quality
| Case | Linkage Rate | Expected UI |
|------|--------------|-------------|
| High coverage | 78% (78/100 PRs) | ✓ Green, "Good coverage" |
| Medium coverage | 55% (55/100 PRs) | ⚠️ Yellow, "Partial coverage" |
| Low coverage | 30% (30/100 PRs) | 🔴 Red, "Low coverage - may not be representative" |
| Zero coverage | 0% (0/100 PRs) | Show "No PRs linked to Jira yet" |
| 100% coverage | 100% (all linked) | ✓ Green, "All PRs linked" |

#### Onboarding Sync Flow
| Case | Scenario | Expected |
|------|----------|----------|
| GitHub only | User skips Jira | Normal flow, no Jira phases |
| Jira during onboarding | User connects Jira | Shows "Syncing Jira issues" phase |
| Jira after onboarding | User adds Jira later | Triggers Jira sync, re-runs LLM for PRs |
| Jira sync fails | API error during sync | Error shown, GitHub data still works |
| Partial Jira sync | Some projects fail | Sync what we can, log errors |

### Factory Enhancements

**File:** `apps/metrics/tests/factories.py`

```python
class JiraIssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = JiraIssue

    team = factory.SubFactory(TeamFactory)
    jira_key = factory.Sequence(lambda n: f"PROJ-{n}")
    jira_id = factory.Sequence(lambda n: str(10000 + n))
    summary = factory.Faker("sentence")
    issue_type = factory.Iterator(["Story", "Bug", "Task"])
    status = "Done"
    story_points = factory.LazyFunction(lambda: Decimal(random.choice([1, 2, 3, 5, 8, 13])))

    # New fields
    time_in_status = factory.LazyFunction(lambda: {
        "In Progress": round(random.uniform(2, 20), 1),
        "Code Review": round(random.uniform(1, 10), 1),
    })
    status_transitions = factory.LazyFunction(lambda: random.randint(2, 6))

    class Params:
        no_story_points = factory.Trait(story_points=None)
        complex_history = factory.Trait(
            time_in_status={"Open": 1.0, "In Progress": 8.0, "Review": 12.0, "In Progress": 4.0, "Done": 0.0},
            status_transitions=5
        )
        no_transitions = factory.Trait(time_in_status={}, status_transitions=0)
```

### Test File Structure

```
apps/
├── integrations/tests/
│   ├── services/
│   │   ├── test_jira_sync.py           # Changelog parsing, time-in-status
│   │   ├── test_jira_client.py         # API retry logic, SP field config
│   │   └── test_jira_utils.py          # should_include_jira_context()
│   └── test_jira_key_extraction.py     # Title/branch extraction edge cases
├── metrics/tests/
│   ├── services/
│   │   └── test_jira_metrics.py        # Dashboard metrics with SP
│   └── prompts/
│       └── test_jira_prompt_render.py  # LLM prompt with Jira context
└── insights/tests/
    └── test_jira_insights.py           # Insight generation with Jira data
```

### Unit Test Coverage

#### 1. Changelog Parsing (`test_jira_sync.py`)
```python
def test_parse_changelog_normal_flow():
    """Issue goes Open → In Progress → Review → Done."""

def test_parse_changelog_empty():
    """Issue with no status changes."""

def test_parse_changelog_circular():
    """Issue bounces between statuses (rework)."""

def test_parse_changelog_reopened():
    """Issue reopened after being Done."""
```

#### 2. Feature Gating (`test_jira_utils.py`)
```python
def test_should_include_jira_context_all_enabled():
    """Returns True when flag ON, integration exists, data synced."""

def test_should_include_jira_context_flag_off():
    """Returns False when feature flag is OFF."""

def test_should_include_jira_context_no_integration():
    """Returns False when team has no JiraIntegration."""

def test_should_include_jira_context_no_data():
    """Returns False when integration exists but no JiraIssue records."""
```

#### 3. LLM Prompt Rendering (`test_jira_prompt_render.py`)
```python
def test_render_pr_prompt_with_jira_context():
    """Jira section included when data provided."""

def test_render_pr_prompt_without_jira():
    """No Jira section when data is None."""

def test_render_pr_prompt_truncates_description():
    """Description truncated at 500 chars with ellipsis."""

def test_render_pr_prompt_time_in_status_format():
    """Time-in-status renders as 'Status: X.Xh, Status: Y.Yh'."""
```

#### 4. Dashboard Metrics (`test_jira_metrics.py`)
```python
def test_get_jira_sprint_metrics_with_sp():
    """Aggregates story points correctly."""

def test_get_jira_sprint_metrics_null_sp():
    """Handles issues without story points."""

def test_get_pr_jira_correlation_sparse_linkage():
    """Calculates correct linkage rate with partial data."""

def test_get_story_point_correlation_buckets():
    """SP buckets match expected ranges."""
```

### Integration Tests

```python
# apps/integrations/tests/test_jira_integration.py

class JiraIntegrationE2ETest(TestCase):
    """End-to-end tests for Jira data flow."""

    def test_full_sync_with_changelog(self):
        """Sync captures time-in-status from changelog."""

    def test_pr_analysis_includes_jira_context(self):
        """LLM analysis receives Jira data when available."""

    def test_insight_generation_with_jira_metrics(self):
        """Weekly insight includes Jira delivery metrics."""

    def test_graceful_degradation_no_jira(self):
        """System works normally when Jira not connected."""
```

### Manual Testing Checklist

1. **Setup**
   - [ ] Connect Jira via OAuth
   - [ ] Select projects to track
   - [ ] Wait for sync (or trigger manually)

2. **Data Verification**
   - [ ] JiraIssue records created with correct fields
   - [ ] `time_in_status` populated from changelog
   - [ ] `story_points` matches Jira (check custom field)

3. **PR Linkage**
   - [ ] PR with key in title shows linked Jira
   - [ ] PR with key in branch shows linked Jira
   - [ ] PR with key only in body does NOT link (by design)

4. **Dashboard Enrichment**
   - [ ] Overview shows SP velocity metrics
   - [ ] Team view shows per-developer SP
   - [ ] Performance shows SP trends
   - [ ] PR detail shows Jira card

5. **LLM Integration**
   - [ ] PR analysis prompt includes Jira context
   - [ ] Weekly insight mentions Jira metrics

6. **Edge Cases**
   - [ ] Feature flag OFF hides all Jira data
   - [ ] Team without Jira sees normal dashboard
   - [ ] Issues without SP handled gracefully

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Model updates + migrations | 0.5 day |
| Jira sync enhancement (changelog, phased sync) | 1.5 days |
| Jira key extraction verification | 0.25 day |
| Onboarding integration + sync status UI | 1 day |
| LLM prompt enhancement | 1 day |
| Insights integration | 1 day |
| Dashboard enrichment (+ linkage indicator) | 1.5 days |
| Unit tests (edge cases, factories) | 1.5 days |
| Integration tests (onboarding flow) | 0.75 day |
| Manual testing + fixes | 0.5 day |
| **Total** | ~9.5 days |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Changelog API increases payload size | Only sync changelog for recently updated issues |
| Story points field varies | Default 10016 + user override + log warning if null |
| Token budget exceeded | Truncate description at 500 chars |
| Jira API rate limits | Retry with exponential backoff, nightly sync pattern |

---

## Critical Considerations (From Plan Review)

### 1. Changelog API Performance & Storage
**Issue:** Adding `expand="changelog"` increases response size 10-50x.

**What we extract from changelog:**
- Status field changes only (not all field changes)
- Calculate time between each status transition
- Count total transitions (rework indicator)

**What we DON'T store:**
- Full changelog history (too large)
- Non-status field changes (not needed)

**Solution:** Fetch changelog separately, parse on-the-fly, store derived metrics:
```python
# First: Fetch issues without changelog (fast)
issues = get_project_issues(credential, project_key)

# Then: Fetch changelog only for issues updated since last sync
for issue in issues_needing_changelog:
    changelog = get_issue_changelog(credential, issue.jira_key)
    # Parse and store derived data only
    issue.time_in_status = _calculate_time_in_status(changelog)
    issue.status_transitions = _count_status_transitions(changelog)
```

**Status naming across teams:**
- MVP: Store raw status names as-is from Jira (e.g., `{"In Progress": 8.5, "Code Review": 12.0}`)
- No mapping required - works immediately
- Future enhancement: Optional status category mapping in team settings

```python
# MVP: Raw statuses shown directly
time_in_status = {"In Progress": 8.5, "Code Review": 12.0, "QA": 4.0}

# Future: Optional category mapping (team setting)
status_categories = {
    "In Progress": "in_progress",
    "Code Review": "review",
    "QA": "testing",
}
```

### 2. Story Points Field - Dynamic Fields List
**Issue:** Current code hardcodes `customfield_10016` in `jira_client.py` (line 116).
**Solution:** Make fields list dynamic based on team's `story_points_field` setting:
```python
def get_project_issues(credential, project_key, story_points_field="customfield_10016"):
    fields = [
        "summary", "status", "issuetype", "priority", "labels",
        "description", "assignee", "created", "resolutiondate",
        story_points_field,  # Dynamic!
    ]
```

### 3. PROMPT_VERSION Bump Required
**Issue:** Per CLAUDE.md, modifying prompt templates requires version bump.
**Solution:** Add to LLM tasks:
- Bump `PROMPT_VERSION` in `apps/metrics/prompts/constants.py`
- Update both PR analysis and insight templates

### 4. GIN Index for time_in_status
**Issue:** No index for new JSONField, slow bottleneck queries.
**Solution:** Add to migration:
```python
from django.contrib.postgres.indexes import GinIndex

indexes = [
    GinIndex(fields=["time_in_status"], name="jira_time_in_status_gin_idx"),
]
```

### 5. Re-processing Existing PRs
**Issue:** PRs processed before Jira sync won't have Jira context in `llm_summary`.
**Solution:** Add management command to re-queue PRs for LLM analysis:
```bash
./manage.py reprocess_prs_with_jira --team-id=123
```
Or trigger automatically when Jira first connected.

### 6. Jira Description Format (ADF)
**Issue:** Jira Cloud returns descriptions as Atlassian Document Format (JSON), not plain text.
**Solution:** Add ADF-to-text converter:
```python
def adf_to_text(adf_content: dict) -> str:
    """Convert Atlassian Document Format to plain text."""
    # Extract text nodes from ADF JSON structure
    # Or use atlassian-python-api's built-in renderer
```

### 7. Existing Insight Template Has Jira Section
**Issue:** `insight/user.jinja2` already has `{% if jira %}` section (lines 103-117).
**Solution:** Review existing section, extend rather than duplicate:
```jinja2
{# Existing section - enhance, don't replace #}
{% if jira %}
## Jira Delivery Metrics
{# Add new fields here #}
{% endif %}
```

### 8. Jira Key Validation
**Issue:** Extracted Jira keys may not belong to tracked projects.
**Solution:** Validate during PR sync:
```python
def validate_jira_key(team, jira_key: str) -> bool:
    """Check if Jira key belongs to a tracked project."""
    project_prefix = jira_key.split("-")[0]
    return TrackedJiraProject.objects.filter(
        team=team,
        project_key=project_prefix,
        is_active=True
    ).exists()
```

### 9. Keep Jira Pipeline Independent
**Issue:** Merging Jira into GitHub pipeline increases complexity and failure risk.
**Decision:** Keep `start_jira_onboarding_pipeline` independent:
- Jira sync failure should NOT block GitHub data
- Run Jira sync after GitHub completes (if connected)
- Update sync status UI to show Jira as separate phase
- Re-trigger LLM processing after Jira sync if PRs have Jira keys

---

## Additional Estimated Effort (From Review)

| Issue | Effort |
|-------|--------|
| Changelog pagination + separate fetch | +0.5 day |
| ADF-to-text converter | +0.25 day |
| Re-processing existing PRs | +0.5 day |
| Jira key validation | +0.25 day |
| **Total additional** | +1.5 days |

**Updated Total: ~11 days**
