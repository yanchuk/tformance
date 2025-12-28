# Onboarding Optimization - Context & Key Files

**Last Updated:** 2025-12-28

## Quick Reference

### Goal
Reduce time-to-first-insight from 10-30 minutes to <2 minutes after GitHub connection.

### Key Changes
1. Make member sync async (removes 10-30s blocking)
2. Implement two-phase sync (7-day quick → 90-day full)
3. Add progressive dashboard with sync indicators
4. Defer LLM analysis to background batch

---

## Critical Files

### OAuth & Team Creation

| File | Purpose | Key Lines |
|------|---------|-----------|
| `apps/auth/views.py` | Unified OAuth callback handler | 181-185 (member sync call), 265 (integration callback) |
| `apps/auth/oauth_state.py` | OAuth state creation/verification | - |
| `apps/onboarding/views.py` | Onboarding wizard views | 271 (redirect after repos) |
| `apps/onboarding/urls.py` | Onboarding URL patterns | - |

### Repository Selection & Sync

| File | Purpose | Key Lines |
|------|---------|-----------|
| `apps/integrations/views/github.py` | GitHub integration views | 343-456 (repo toggle), 284 (repos list) |
| `apps/integrations/models.py` | TrackedRepository model | 145-281 (sync progress fields) |
| `apps/integrations/tasks.py` | Celery sync tasks | `sync_repository_initial_task`, `sync_historical_data_task` |
| `apps/integrations/services/github_sync.py` | GitHub API calls, PR processing | `_process_prs()` |
| `apps/integrations/services/onboarding_sync.py` | Onboarding sync orchestration | `OnboardingSyncService` |
| `apps/integrations/services/member_sync.py` | Member sync logic | `sync_github_members()` |

### Dashboard & UI

| File | Purpose |
|------|---------|
| `apps/web/views.py` | Dashboard main view |
| `templates/web/app_home.html` | Dashboard template |
| `templates/onboarding/sync_progress.html` | Sync progress page |
| `templates/onboarding/select_repos.html` | Repo selection UI |
| `apps/metrics/services/quick_stats.py` | Dashboard stat calculations |
| `apps/integrations/services/status.py` | Team integration status |

### AI Detection

| File | Purpose |
|------|---------|
| `apps/metrics/services/ai_patterns.py` | Regex pattern detection (instant) |
| `apps/integrations/services/groq_batch.py` | LLM batch processing (slow) |
| `apps/metrics/services/llm_prompts.py` | LLM prompt templates |

---

## Model Fields Reference

### TrackedRepository (apps/integrations/models.py)

```python
# Sync status tracking
sync_status = CharField(choices=[pending, syncing, complete, error])
sync_progress = IntegerField(default=0)  # 0-100%
sync_prs_total = IntegerField(null=True)
sync_prs_completed = IntegerField(default=0)
sync_started_at = DateTimeField(null=True)
last_sync_at = DateTimeField(null=True)
last_sync_error = TextField(null=True)

# Rate limiting
rate_limit_remaining = IntegerField(null=True)
rate_limit_reset_at = DateTimeField(null=True)
```

### PullRequest (apps/metrics/models/github.py)

```python
# Key fields for quick insights
state = CharField()  # open, merged, closed
merged_at = DateTimeField(null=True)
cycle_time_hours = DecimalField(null=True)  # Calculated
review_time_hours = DecimalField(null=True)

# AI detection
is_ai_assisted = BooleanField(null=True)
ai_tools_detected = ArrayField(null=True)
llm_summary = JSONField(null=True)  # LLM analysis result
patterns_version = CharField()  # Regex pattern version
```

---

## Key Decisions Made

### 1. Two-Phase Sync Strategy
- **Quick sync:** 7 days, pattern detection only, enables dashboard
- **Full sync:** 90 days, includes LLM analysis, runs in background
- **Rationale:** 7 days provides enough data for initial insights; LLM can wait

### 2. Pattern Detection vs LLM
- **Pattern detection:** Instant, ~85% accuracy, sufficient for quick insights
- **LLM analysis:** 0.5-2s per PR, higher accuracy, deferred to background
- **Rationale:** Speed trumps accuracy for initial view; LLM enhances later

### 3. Async Member Sync
- **Current:** Blocks OAuth callback for 10-30s on large orgs
- **New:** Queue as Celery task, complete in background
- **Rationale:** Members aren't needed immediately; PRs can have NULL author

### 4. Progressive Dashboard
- **Current:** Empty until ALL sync complete
- **New:** Show available data with "syncing" indicator
- **Rationale:** Better UX; user sees value immediately

---

## Celery Tasks Reference

### Current Tasks
```python
# Initial sync for newly tracked repo
sync_repository_initial_task(repo_id, days_back=30)

# Historical data sync (onboarding)
sync_historical_data_task(team_id, repo_ids=[])

# Daily incremental sync
sync_all_repositories_task()  # Runs at 4:00 AM UTC

# Member sync
sync_github_members_task(integration_id)  # Runs at 4:15 AM UTC
```

### New Tasks (To Be Created)
```python
# Quick sync for fast insights
sync_quick_data_task(team_id, repo_ids=[], days=7)

# Full historical sync (after quick)
sync_full_history_task(team_id, repo_ids=[], days=90)

# Batch LLM analysis
queue_llm_analysis_batch_task(team_id, pr_ids=[])

# Async webhook creation
create_repository_webhooks_task(repo_ids=[])
```

---

## URL Patterns

### Onboarding Flow
```
/onboarding/                    → start
/onboarding/github/             → github_connect
/onboarding/org/                → select_org (if multiple)
/onboarding/repos/              → select_repos
/onboarding/sync/               → sync_progress  ← REDIRECT HERE
/onboarding/jira/               → connect_jira
/onboarding/slack/              → connect_slack
/onboarding/complete/           → complete
```

### OAuth Callbacks
```
/auth/github/callback/          → github_callback
/auth/jira/callback/            → jira_callback
```

### Integration Management
```
/a/<team_slug>/integrations/github/repos/              → repo list
/a/<team_slug>/integrations/github/repos/<id>/toggle/  → track/untrack
/a/<team_slug>/integrations/github/repos/<id>/progress/ → sync progress (HTMX)
```

---

## Session Keys

```python
ONBOARDING_TOKEN_KEY = "onboarding_github_token"
ONBOARDING_ORGS_KEY = "onboarding_github_orgs"
ONBOARDING_SELECTED_ORG_KEY = "onboarding_selected_org"
"sync_task_id"  # Celery task ID for progress polling
```

---

## Signals

```python
# apps/integrations/signals.py
onboarding_sync_started     # Sent when sync begins
repository_sync_completed   # Sent per repo
onboarding_sync_completed   # Sent when all repos done
```

---

## API Rate Limits

| Service | Limit | Notes |
|---------|-------|-------|
| GitHub REST API | 5,000/hour (with token) | Per integration |
| GitHub GraphQL | 5,000 points/hour | More efficient for PRs |
| Groq LLM | Varies by plan | Batch to avoid limits |

---

## Testing Files

```
apps/auth/tests/test_oauth_state.py          # OAuth state tests
apps/integrations/tests/test_member_sync.py  # Member sync tests
apps/integrations/tests/test_github_sync.py  # Sync service tests
apps/integrations/tests/test_tasks.py        # Celery task tests
apps/onboarding/tests/test_views.py          # Onboarding view tests
tests/e2e/onboarding.spec.ts                 # E2E onboarding tests
```

---

## Environment Variables

```
GITHUB_CLIENT_ID       # OAuth app client ID
GITHUB_SECRET_ID       # OAuth app client secret
GROQ_API_KEY           # LLM API key
USE_GRAPHQL=True       # Enable GraphQL for sync (optional)
```

---

## Related PRD Documents

- `prd/ONBOARDING.md` - User onboarding flow spec
- `prd/IMPLEMENTATION-PLAN.md` - Phase 9 covers onboarding polish
- `prd/ARCHITECTURE.md` - Overall system architecture
- `prd/DATA-MODEL.md` - Database schema reference
