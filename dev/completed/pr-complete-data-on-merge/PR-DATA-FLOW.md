# PR Data Flow: Webhooks vs API

**Last Updated:** 2025-12-22

This document explains how Pull Request data flows into the system, what data we receive from each source, and how it's processed.

---

## Table of Contents

1. [Overview](#overview)
2. [Data Sources](#data-sources)
3. [Webhook Flow](#webhook-flow)
4. [API Fetch Flow](#api-fetch-flow)
5. [Data Models](#data-models)
6. [Field-by-Field Comparison](#field-by-field-comparison)
7. [Processing Pipeline](#processing-pipeline)
8. [Timing & Triggers](#timing--triggers)

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PR DATA ACQUISITION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────┐              ┌──────────────────┐                    │
│   │   WEBHOOKS       │              │   API FETCH      │                    │
│   │   (Real-time)    │              │   (On-demand)    │                    │
│   └────────┬─────────┘              └────────┬─────────┘                    │
│            │                                  │                              │
│            ▼                                  ▼                              │
│   ┌──────────────────┐              ┌──────────────────┐                    │
│   │ pull_request     │              │ Triggered when:  │                    │
│   │ pull_request_    │              │ - PR merged      │                    │
│   │ review           │              │ - Historical sync│                    │
│   └────────┬─────────┘              │ - Incremental    │                    │
│            │                        └────────┬─────────┘                    │
│            ▼                                  │                              │
│   ┌──────────────────┐                       │                              │
│   │ PullRequest      │◄──────────────────────┘                              │
│   │ PRReview         │                                                       │
│   │ (basic data)     │              ┌──────────────────┐                    │
│   └──────────────────┘              │ + Commit         │                    │
│                                     │ + PRFile         │                    │
│                                     │ + PRCheckRun     │                    │
│                                     │ + PRComment      │                    │
│                                     │ + Iteration      │                    │
│                                     │   Metrics        │                    │
│                                     └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Insight:** Webhooks give us speed, API fetches give us completeness.

---

## Data Sources

### 1. GitHub Webhooks (Real-time)

| Event | Trigger | Data Received |
|-------|---------|---------------|
| `pull_request` | PR opened, closed, merged, edited, etc. | PR metadata, state, timestamps |
| `pull_request_review` | Review submitted | Review state, reviewer, timestamp |

**Subscribed in:** `apps/integrations/services/github_webhooks.py:42`
```python
events=["pull_request", "pull_request_review"]
```

### 2. GitHub API Fetches (On-demand)

| Trigger | When | What's Fetched |
|---------|------|----------------|
| `fetch_pr_complete_data_task` | PR merged via webhook | Commits, files, check runs, comments |
| `sync_repository_history` | Initial repo setup | All PRs + all related data |
| `sync_repository_incremental` | Daily scheduled task | Updated PRs since last sync |

---

## Webhook Flow

### Pull Request Event (`pull_request`)

**Entry Point:** `apps/web/views.py:108` → `github_webhook()`

```
GitHub Server
     │
     │ POST /webhooks/github/
     │ Headers: X-GitHub-Event: pull_request
     │          X-Hub-Signature-256: sha256=...
     │          X-GitHub-Delivery: <uuid>
     ▼
┌─────────────────────────────────────────┐
│ github_webhook() view                   │
│ 1. Validate signature (HMAC-SHA256)     │
│ 2. Check replay protection (cache)      │
│ 3. Look up TrackedRepository            │
│ 4. Dispatch to handler                  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ handle_pull_request_event()             │
│ apps/metrics/processors.py:199          │
│                                         │
│ 1. Extract PR data from payload         │
│ 2. Map GitHub fields to model fields    │
│ 3. Create/update PullRequest record     │
│ 4. If merged: trigger background tasks  │
└────────────────┬────────────────────────┘
                 │
                 │ (if action="closed" AND merged=true)
                 ▼
┌─────────────────────────────────────────┐
│ _trigger_pr_surveys_if_merged()         │
│                                         │
│ Dispatches (independently):             │
│ • send_pr_surveys_task (Slack surveys)  │
│ • post_survey_comment_task (GH comment) │
│ • fetch_pr_complete_data_task (NEW)     │
└─────────────────────────────────────────┘
```

### Webhook Payload Structure

```json
{
    "action": "closed",
    "pull_request": {
        "id": 1234567890,           // → github_pr_id (unique identifier)
        "number": 42,               // → used for API calls
        "title": "Add feature X",   // → title
        "state": "closed",          // → combined with merged for state
        "merged": true,             // → determines "merged" vs "closed" state
        "merged_at": "2025-01-02T15:00:00Z",  // → merged_at
        "created_at": "2025-01-01T10:00:00Z", // → pr_created_at
        "user": {
            "id": 12345,            // → author lookup via github_id
            "login": "developer"
        },
        "additions": 150,           // → additions
        "deletions": 50,            // → deletions
        "head": {
            "ref": "feature/PROJ-123-new-feature"  // → jira_key extraction
        }
    },
    "repository": {
        "id": 98765,                // → used to find TrackedRepository
        "full_name": "owner/repo"   // → github_repo
    }
}
```

### What Webhooks Give Us

| Field | Source | Business Value |
|-------|--------|----------------|
| `github_pr_id` | `pull_request.id` | Unique identifier for deduplication |
| `github_repo` | `repository.full_name` | Links PR to tracked repository |
| `title` | `pull_request.title` | Display, revert/hotfix detection |
| `state` | Derived from `state` + `merged` | PR lifecycle tracking |
| `author` | Lookup by `user.id` | Attribution, metrics |
| `pr_created_at` | `pull_request.created_at` | Cycle time calculation |
| `merged_at` | `pull_request.merged_at` | Cycle time calculation |
| `additions/deletions` | `pull_request.*` | Code volume metrics |
| `jira_key` | Extracted from title/branch | Jira correlation |

### What Webhooks DON'T Give Us

| Missing Data | Why | Impact |
|--------------|-----|--------|
| Commits | No `push` event subscription | Can't track commit patterns |
| Files changed | Not in PR webhook payload | No file-level metrics |
| Check runs | No `check_run` event | No CI/CD duration tracking |
| Comments | No comment events | Can't count discussions |
| Iteration metrics | Requires commits + reviews | No review_rounds, fix_response |

---

## API Fetch Flow

### Triggered by `fetch_pr_complete_data_task`

**Entry Point:** `apps/integrations/tasks.py` (after PR merge webhook)

```
PR Merged Webhook
       │
       │ fetch_pr_complete_data_task.delay(pr.id)
       ▼
┌─────────────────────────────────────────┐
│ fetch_pr_complete_data_task(pr_id)      │
│                                         │
│ 1. Look up PullRequest by ID            │
│ 2. Find TrackedRepository               │
│ 3. Get decrypted access_token           │
│ 4. Call sync functions:                 │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┬────────────┬────────────┐
    ▼            ▼            ▼            ▼            ▼
┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│sync_pr_│ │sync_pr_│ │sync_pr_  │ │sync_pr_  │ │sync_pr_  │
│commits │ │files   │ │check_runs│ │issue_    │ │review_   │
│        │ │        │ │          │ │comments  │ │comments  │
└───┬────┘ └───┬────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
    │          │           │            │            │
    ▼          ▼           ▼            ▼            ▼
┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────────────────┐
│Commit  │ │PRFile  │ │PRCheckRun│ │PRComment             │
│model   │ │model   │ │model     │ │(type=issue/review)   │
└────────┘ └────────┘ └──────────┘ └──────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ calculate_pr_iteration_metrics(pr)      │
│                                         │
│ Updates PullRequest with:               │
│ • total_comments                        │
│ • commits_after_first_review            │
│ • review_rounds                         │
│ • avg_fix_response_hours                │
└─────────────────────────────────────────┘
```

### API Calls Made

| Function | GitHub API Endpoint | Data Retrieved |
|----------|---------------------|----------------|
| `sync_pr_commits` | `GET /repos/{owner}/{repo}/pulls/{pr_number}/commits` | All commits in PR |
| `sync_pr_files` | `GET /repos/{owner}/{repo}/pulls/{pr_number}/files` | All files changed |
| `sync_pr_check_runs` | `GET /repos/{owner}/{repo}/commits/{sha}/check-runs` | CI/CD status for head |
| `sync_pr_issue_comments` | `GET /repos/{owner}/{repo}/issues/{pr_number}/comments` | General PR comments |
| `sync_pr_review_comments` | `GET /repos/{owner}/{repo}/pulls/{pr_number}/comments` | Inline code comments |

### What API Fetches Give Us

#### Commits (`Commit` model)

```python
{
    "github_sha": "abc123...",      # Unique commit identifier
    "github_repo": "owner/repo",
    "author": TeamMember,            # Mapped via github_id
    "message": "Fix bug in...",     # Commit message
    "committed_at": datetime,        # When committed
    "additions": 50,                 # Lines added
    "deletions": 20,                 # Lines removed
    "pull_request": PullRequest,     # FK to PR
    "is_ai_assisted": bool,          # AI co-author detection
    "ai_co_authors": ["claude"],     # List of AI tools
}
```

**Business Value:**
- Track commit patterns per developer
- Detect AI-assisted commits (co-author trailers)
- Calculate `commits_after_first_review` metric
- Measure fix response time

#### Files (`PRFile` model)

```python
{
    "pull_request": PullRequest,     # FK to PR
    "filename": "src/api/users.ts",  # Full path
    "status": "modified",            # added/modified/removed/renamed
    "additions": 30,
    "deletions": 10,
    "changes": 40,                   # Total changes
    "file_category": "backend",      # Categorized: frontend/backend/test/docs/config
}
```

**Business Value:**
- Understand code distribution (frontend vs backend)
- Track test coverage patterns
- Identify high-churn files

#### Check Runs (`PRCheckRun` model)

```python
{
    "github_check_run_id": 123456,
    "pull_request": PullRequest,
    "name": "pytest",                # Check name
    "status": "completed",           # queued/in_progress/completed
    "conclusion": "success",         # success/failure/skipped/etc.
    "started_at": datetime,
    "completed_at": datetime,
    "duration_seconds": 120,         # Auto-calculated
}
```

**Business Value:**
- Track CI/CD reliability
- Measure build times
- Identify flaky tests

#### Comments (`PRComment` model)

```python
{
    "github_comment_id": 789012,
    "pull_request": PullRequest,
    "author": TeamMember,
    "body": "Consider using...",     # Comment text
    "comment_type": "review",        # "issue" or "review" (inline)
    "path": "src/api/users.ts",      # For review comments
    "line": 42,                      # For review comments
    "in_reply_to_id": 789010,        # Thread parent
    "comment_created_at": datetime,
}
```

**Business Value:**
- Track code review thoroughness
- Identify discussion patterns
- Calculate `total_comments` metric

---

## Data Models

### Entity Relationship

```
┌─────────────┐
│    Team     │
└──────┬──────┘
       │
       │ 1:N
       ▼
┌─────────────┐     1:N     ┌─────────────┐
│ TeamMember  │◄────────────│ PullRequest │
└─────────────┘  (author)   └──────┬──────┘
       ▲                           │
       │                           │ 1:N
       │ (reviewer)                ├────────────┬────────────┬────────────┐
       │                           ▼            ▼            ▼            ▼
┌──────┴──────┐              ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐
│  PRReview   │              │  Commit  │ │  PRFile  │ │PRCheckRun │ │PRComment │
└─────────────┘              └──────────┘ └──────────┘ └───────────┘ └──────────┘
```

### PullRequest Fields Summary

| Field | Source | Populated By |
|-------|--------|--------------|
| `github_pr_id` | GitHub | Webhook / Sync |
| `github_repo` | GitHub | Webhook / Sync |
| `title` | GitHub | Webhook / Sync |
| `body` | GitHub | **NOT CAPTURED** |
| `author` | Lookup | Webhook / Sync |
| `state` | Derived | Webhook / Sync |
| `pr_created_at` | GitHub | Webhook / Sync |
| `merged_at` | GitHub | Webhook / Sync |
| `first_review_at` | Calculated | Webhook (review event) / Sync |
| `cycle_time_hours` | Calculated | Webhook / Sync |
| `review_time_hours` | Calculated | Webhook (review event) / Sync |
| `additions` | GitHub | Webhook / Sync |
| `deletions` | GitHub | Webhook / Sync |
| `is_revert` | Derived | Webhook / Sync (from title) |
| `is_hotfix` | Derived | Webhook / Sync (from title) |
| `jira_key` | Extracted | Webhook / Sync (from title/branch) |
| `review_rounds` | Calculated | **API fetch only** |
| `avg_fix_response_hours` | Calculated | **API fetch only** |
| `commits_after_first_review` | Calculated | **API fetch only** |
| `total_comments` | Calculated | **API fetch only** |
| `is_ai_assisted` | Detection | **Future** |
| `ai_tools_detected` | Detection | **Future** |

---

## Field-by-Field Comparison

### Basic PR Data

| Field | Webhook | API | Notes |
|-------|:-------:|:---:|-------|
| PR ID | ✅ | ✅ | Same from both |
| Title | ✅ | ✅ | Same from both |
| State | ✅ | ✅ | Same from both |
| Author | ✅ | ✅ | Same from both |
| Created at | ✅ | ✅ | Same from both |
| Merged at | ✅ | ✅ | Same from both |
| Additions | ✅ | ✅ | Same from both |
| Deletions | ✅ | ✅ | Same from both |

### Related Data

| Data Type | Webhook | API | Notes |
|-----------|:-------:|:---:|-------|
| Reviews | ✅ (event) | ✅ | Webhook gives real-time, API backfills |
| Commits | ❌ | ✅ | API only |
| Files | ❌ | ✅ | API only |
| Check Runs | ❌ | ✅ | API only |
| Comments | ❌ | ✅ | API only |

### Calculated Metrics

| Metric | From Webhook | From API | Calculation |
|--------|:------------:|:--------:|-------------|
| `cycle_time_hours` | ✅ | ✅ | `merged_at - pr_created_at` |
| `review_time_hours` | ✅ | ✅ | `first_review_at - pr_created_at` |
| `review_rounds` | ❌ | ✅ | Count of `changes_requested` → commit cycles |
| `avg_fix_response_hours` | ❌ | ✅ | Avg time from `changes_requested` to next commit |
| `commits_after_first_review` | ❌ | ✅ | Count commits after `first_review_at` |
| `total_comments` | ❌ | ✅ | Count of PRComment records |

---

## Processing Pipeline

### Webhook Processing (`processors.py`)

```python
def _map_github_pr_to_fields(team, pr_data: dict) -> dict:
    """
    Transforms GitHub payload to model fields.

    Input: Raw webhook payload['pull_request']
    Output: Dict ready for PullRequest.objects.update_or_create()

    Processing:
    1. Extract basic fields (title, additions, deletions)
    2. Determine state (open/closed/merged)
    3. Look up author by github_id
    4. Parse timestamps (ISO8601 → datetime)
    5. Calculate cycle_time if merged
    6. Detect flags (is_revert, is_hotfix)
    7. Extract jira_key from title or branch
    """
```

### API Processing (`github_sync.py`)

```python
def sync_pr_commits(pr, pr_number, access_token, repo_full_name, team, errors):
    """
    Fetches commits via PyGithub and creates Commit records.

    For each commit:
    1. Extract SHA, message, timestamps
    2. Look up author by github_id
    3. Get additions/deletions from stats
    4. Create/update Commit record

    Returns: Number of commits synced
    """

def calculate_pr_iteration_metrics(pr):
    """
    Calculates derived metrics from synced data.

    Requires: Commits + Reviews already synced

    Calculations:
    1. total_comments = PRComment.filter(pull_request=pr).count()
    2. commits_after_first_review = Commit.filter(
           pull_request=pr,
           committed_at__gt=first_review.submitted_at
       ).count()
    3. review_rounds = count changes_requested→commit cycles
    4. avg_fix_response_hours = mean(commit_time - review_time)
    """
```

---

## Timing & Triggers

### When Each Data Source Runs

| Trigger | Data Source | Latency | Data Completeness |
|---------|-------------|---------|-------------------|
| PR opened | Webhook | ~1s | Basic PR data |
| PR edited | Webhook | ~1s | Updated title/description |
| Review submitted | Webhook | ~1s | Review record |
| PR merged | Webhook + API task | ~5-30s | Complete data |
| Daily sync | API | ~hours | Catch missed events |
| Initial sync | API | ~minutes | Historical data |

### Task Execution Timeline

```
Time ─────────────────────────────────────────────────────────►

PR Merged
    │
    ├─── Webhook received (0s)
    │    └── PullRequest updated (state=merged)
    │
    ├─── Tasks queued (0.1s)
    │    ├── send_pr_surveys_task
    │    ├── post_survey_comment_task
    │    └── fetch_pr_complete_data_task
    │
    ├─── fetch_pr_complete_data_task starts (1-5s)
    │    ├── sync_pr_commits (~2s)
    │    ├── sync_pr_files (~1s)
    │    ├── sync_pr_check_runs (~1s)
    │    ├── sync_pr_issue_comments (~1s)
    │    ├── sync_pr_review_comments (~1s)
    │    └── calculate_pr_iteration_metrics (~0.1s)
    │
    └─── Complete data available (~10-30s after merge)
```

---

## Summary

| Aspect | Webhooks | API Fetch |
|--------|----------|-----------|
| **Speed** | Real-time (~1s) | Background (~10-30s) |
| **Coverage** | PR + Reviews only | Everything |
| **Reliability** | May miss events | Complete backfill |
| **API Cost** | 0 calls | ~5 calls per PR |
| **When Used** | Always on | On merge + daily sync |

**Best Practice:** Use webhooks for immediate state updates, API fetch for complete data on merge, daily sync as safety net.
