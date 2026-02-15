---
name: integration-pipeline-flow
description: Data flow from external integrations through processing to dashboards. Triggers on GitHub sync, Jira sync, webhook, OAuth, data pipeline, sync service, Celery task. Understanding upstream/downstream effects.
---

# Integration Pipeline Flow

## Purpose

Map how data flows from external services (GitHub, Jira, Slack) through processing to dashboards.

## When to Use

**Automatically activates when:**
- Working on integration code
- Debugging data sync issues
- Understanding where data comes from
- Adding new data sources

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                            │
├─────────────┬─────────────┬─────────────┬─────────────┬────────────┤
│   GitHub    │    Jira     │    Slack    │   Copilot   │   Surveys  │
│   (OAuth)   │   (OAuth)   │   (OAuth)   │ (via GitHub)│  (Slack)   │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──────┬─────┘
       │             │             │             │             │
       ▼             ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SYNC LAYER                                  │
├─────────────┬─────────────┬─────────────┬─────────────┬────────────┤
│ GitHubSync  │  JiraSync   │  SlackSync  │ CopilotSync │ SurveyProc │
│  Service    │   Service   │   Service   │   Service   │  Service   │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──────┬─────┘
       │             │             │             │             │
       ▼             ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATABASE MODELS                              │
├─────────────┬─────────────┬─────────────┬─────────────┬────────────┤
│ PullRequest │  JiraIssue  │ TeamMember  │AIUsageDaily │  PRSurvey  │
│ PRReview    │             │             │             │            │
│ Commit      │             │             │             │            │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──────┬─────┘
       │             │             │             │             │
       └─────────────┴──────┬──────┴─────────────┴─────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PROCESSING LAYER                               │
├─────────────────────────┬───────────────────────────────────────────┤
│   AI Pattern Detection  │          LLM Analysis                     │
│   (ai_patterns.py)      │       (groq_batch.py)                     │
└───────────┬─────────────┴───────────────┬───────────────────────────┘
            │                             │
            └──────────────┬──────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       SERVICE LAYER                                 │
├─────────────────────────┬───────────────────────────────────────────┤
│    DashboardService     │         PRListService                     │
│    (aggregations)       │       (filtered lists)                    │
└───────────┬─────────────┴───────────────┬───────────────────────────┘
            │                             │
            └──────────────┬──────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION                                 │
├─────────────────────────┬───────────────────────────────────────────┤
│   Dashboard Views       │         API Endpoints                     │
│   (Chart.js + HTMX)     │        (DRF serializers)                  │
└─────────────────────────┴───────────────────────────────────────────┘
```

## Sync Triggers

| Trigger | Service | Frequency |
|---------|---------|-----------|
| Daily Celery | GitHubSyncService | Once/day |
| Daily Celery | JiraSyncService | Once/day |
| Manual button | All sync services | On-demand |
| OAuth connect | Initial sync | Once |

## Key Models by Source

### From GitHub

```
ConnectedAccount (OAuth token)
    ↓
TeamMember (org members)
PullRequest (PRs with metadata)
    ├── PRReview (reviews)
    ├── PRFile (changed files)
    └── Commit (commits)
```

### From Jira

```
ConnectedAccount (OAuth token)
    ↓
JiraIssue (issues/tickets)
    └── linked to PullRequest via branch name or PR body
```

### From Slack

```
ConnectedAccount (OAuth token)
    ↓
PRSurvey (AI usage surveys sent via bot)
    └── linked to PullRequest and TeamMember
```

## Processing Pipeline

### 1. Raw Data → AI Detection

```python
# After GitHub sync, AI patterns run automatically
pr = PullRequest.objects.get(id=pr_id)
# Regex patterns populate:
#   - is_ai_assisted
#   - ai_tools_detected
#   - ai_confidence_score
```

### 2. AI Detection → LLM Analysis

```python
# Batch LLM analysis (Celery task or manual)
from apps.integrations.services.groq_batch import GroqBatchService

service = GroqBatchService(team)
service.analyze_prs(pr_ids)
# Populates: llm_summary JSON field
```

### 3. Models → Dashboard

```python
# Service layer aggregates data
service = DashboardService(team)
metrics = service.get_ai_metrics()
# Uses effective_* properties (LLM priority)
```

## Debugging Data Issues

### Check sync status

```python
from apps.integrations.models import ConnectedAccount

# Is OAuth connected?
account = ConnectedAccount.objects.filter(
    team=team, provider='github'
).first()
print(f"Connected: {account is not None}")
print(f"Last sync: {account.last_sync_at if account else 'N/A'}")
```

### Check PR data

```python
pr = PullRequest.objects.get(id=pr_id)
print(f"Regex AI: {pr.is_ai_assisted}")
print(f"LLM AI: {pr.llm_summary.get('ai', {})}")
print(f"Effective AI: {pr.effective_is_ai_assisted}")
```

### Force resync

```python
from apps.integrations.services.github_sync import GitHubSyncService

service = GitHubSyncService(team)
service.sync_prs(full_sync=True)
```

## Celery Tasks

| Task | Schedule | Purpose |
|------|----------|---------|
| `sync_github_data` | Daily 2am | Full GitHub sync |
| `sync_jira_data` | Daily 3am | Full Jira sync |
| `run_llm_analysis` | Daily 4am | Analyze new PRs |
| `aggregate_weekly` | Monday 5am | Weekly rollups |

## Upstream/Downstream Impact

| Change | Upstream Effect | Downstream Effect |
|--------|-----------------|-------------------|
| New PR field | Sync service change | Dashboard service, templates |
| New AI pattern | ai_patterns.py | Backfill needed, metrics change |
| LLM prompt change | llm_prompts.py | Re-analysis needed |
| New integration | OAuth + sync service | New models, new dashboard |

---

**Enforcement Level**: SUGGEST
**Priority**: Medium
