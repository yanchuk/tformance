# GitHub Data Flow: Complete Reference

**Last Updated:** 2025-12-22

This document explains the complete GitHub data flow - from OAuth connection through all data types we collect, how they're processed, and what business value they provide.

---

## Table of Contents

1. [Overview](#overview)
2. [OAuth Connection Flow](#oauth-connection-flow)
3. [Data Acquisition Methods](#data-acquisition-methods)
4. [Data Models](#data-models)
5. [Member Sync](#member-sync)
6. [Repository Tracking](#repository-tracking)
7. [Pull Request Data](#pull-request-data)
8. [Deployment Data](#deployment-data)
9. [Copilot Metrics](#copilot-metrics)
10. [Webhooks vs API Reference](#webhooks-vs-api-reference)

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         GITHUB DATA ACQUISITION OVERVIEW                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────┐                                                            │
│  │  User connects  │                                                            │
│  │  GitHub OAuth   │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐         │
│  │ GitHubIntegration│────▶│ Member Sync      │────▶│ TeamMember       │         │
│  │ + Credentials   │     │ (org members)    │     │ records          │         │
│  └────────┬────────┘     └──────────────────┘     └──────────────────┘         │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐     ┌──────────────────┐                                   │
│  │ TrackedRepository│────▶│ Webhook Setup    │                                   │
│  │ (user selects)  │     │ (per repo)       │                                   │
│  └────────┬────────┘     └────────┬─────────┘                                   │
│           │                       │                                              │
│           │                       ▼                                              │
│           │              ┌──────────────────┐                                   │
│           │              │ Real-time Events │                                   │
│           │              │ • pull_request   │                                   │
│           │              │ • pull_request_  │                                   │
│           │              │   review         │                                   │
│           │              └────────┬─────────┘                                   │
│           │                       │                                              │
│           ▼                       ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐           │
│  │                        DATA STORES                                │           │
│  ├──────────────────────────────────────────────────────────────────┤           │
│  │ PullRequest │ PRReview │ Commit │ PRFile │ PRCheckRun │ PRComment │           │
│  │ Deployment  │ CopilotMetrics │ AIUsageDaily                      │           │
│  └──────────────────────────────────────────────────────────────────┘           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## OAuth Connection Flow

### Step 1: User Initiates OAuth

**URL:** `/a/{team_slug}/integrations/github/connect/`
**Handler:** `apps/integrations/views/github.py`

```
User clicks "Connect GitHub"
        │
        ▼
┌─────────────────────────────────────┐
│ github_oauth_start()                │
│                                     │
│ 1. Generate random state token      │
│ 2. Store state in session           │
│ 3. Build GitHub OAuth URL           │
│ 4. Redirect to GitHub               │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ GitHub OAuth Authorization Page     │
│                                     │
│ Scopes requested:                   │
│ • read:org (organization info)      │
│ • repo (repository access)          │
│ • read:user (user profile)          │
│ • manage_billing:copilot (optional) │
└─────────────────────────────────────┘
```

### Step 2: OAuth Callback

**URL:** `/integrations/github/callback/`
**Handler:** `apps/integrations/views/github.py:github_oauth_callback()`

```
GitHub redirects with code + state
        │
        ▼
┌─────────────────────────────────────┐
│ github_oauth_callback()             │
│                                     │
│ 1. Validate state token             │
│ 2. Exchange code for access_token   │
│ 3. Fetch user info from GitHub      │
│ 4. Fetch organizations user belongs │
└─────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│ Data Created:                       │
│                                     │
│ OAuthCredential                     │
│ ├─ access_token (ENCRYPTED)         │
│ ├─ refresh_token (ENCRYPTED)        │
│ ├─ token_expires_at                 │
│ └─ github_user_id                   │
│                                     │
│ GitHubIntegration                   │
│ ├─ team (FK)                        │
│ ├─ credential (FK)                  │
│ ├─ github_org_id                    │
│ ├─ github_org_name                  │
│ └─ webhook_secret (generated)       │
└─────────────────────────────────────┘
```

### OAuth Scopes & What They Enable

| Scope | Purpose | Data Enabled |
|-------|---------|--------------|
| `read:org` | Read organization info | Org members, teams |
| `repo` | Full repo access | PRs, commits, files, check runs, comments |
| `read:user` | Read user profile | User details for matching |
| `manage_billing:copilot` | Copilot billing access | Copilot usage metrics |

### Token Storage

**Location:** `apps/integrations/models.py:OAuthCredential`

```python
class OAuthCredential(BaseModel):
    access_token = EncryptedTextField()    # AES-256 encrypted
    refresh_token = EncryptedTextField()   # AES-256 encrypted
    token_expires_at = DateTimeField()
    github_user_id = CharField()
```

**Encryption:** Uses `apps/integrations/services/encryption.py` with Fernet (AES-256-CBC)

---

## Data Acquisition Methods

### Method 1: Webhooks (Real-time)

| Aspect | Details |
|--------|---------|
| **Trigger** | GitHub pushes to our endpoint |
| **Latency** | ~1 second |
| **Events** | `pull_request`, `pull_request_review` |
| **Endpoint** | `POST /webhooks/github/` |
| **Handler** | `apps/web/views.py:github_webhook()` |

### Method 2: API Fetch on Merge

| Aspect | Details |
|--------|---------|
| **Trigger** | PR merged webhook dispatches task |
| **Latency** | ~10-30 seconds |
| **Data** | Commits, files, check runs, comments |
| **Task** | `fetch_pr_complete_data_task` |
| **Handler** | `apps/integrations/tasks.py` |

### Method 3: Historical Sync

| Aspect | Details |
|--------|---------|
| **Trigger** | Repository first tracked |
| **Latency** | Minutes (depends on repo size) |
| **Data** | All PRs + all related data |
| **Task** | `sync_repository_initial_task` |
| **Handler** | `apps/integrations/services/github_sync.py` |

### Method 4: Incremental Sync

| Aspect | Details |
|--------|---------|
| **Trigger** | Daily scheduled task |
| **Latency** | Background (overnight) |
| **Data** | PRs updated since last sync |
| **Task** | `sync_repository_task` |
| **Handler** | `apps/integrations/services/github_sync.py` |

### Method 5: Copilot Metrics Fetch

| Aspect | Details |
|--------|---------|
| **Trigger** | Daily scheduled task |
| **Latency** | Background |
| **Data** | Copilot seat assignments, usage |
| **Task** | `sync_copilot_metrics_task` |
| **Handler** | `apps/integrations/services/copilot_metrics.py` |

---

## Data Models

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA MODEL HIERARCHY                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────┐                                                                    │
│  │  Team   │ (tenant isolation)                                                 │
│  └────┬────┘                                                                    │
│       │                                                                          │
│       ├───────────────────────────────────────────────────────────────┐         │
│       │                                                               │         │
│       ▼                                                               ▼         │
│  ┌───────────────────┐                                    ┌───────────────────┐ │
│  │ GitHubIntegration │                                    │    TeamMember     │ │
│  │ ├─ credential (FK)│                                    │ ├─ github_id      │ │
│  │ ├─ github_org_id  │                                    │ ├─ github_username│ │
│  │ └─ webhook_secret │                                    │ ├─ display_name   │ │
│  └────────┬──────────┘                                    │ ├─ slack_user_id  │ │
│           │                                               │ └─ jira_account_id│ │
│           │                                               └─────────┬─────────┘ │
│           ▼                                                         │           │
│  ┌───────────────────┐                                              │           │
│  │ TrackedRepository │                                              │           │
│  │ ├─ full_name      │                                              │           │
│  │ ├─ github_repo_id │                                              │           │
│  │ ├─ is_active      │                                              │           │
│  │ ├─ last_sync_at   │◄─────────────────────────────────────────────┤           │
│  │ └─ sync_status    │                                              │           │
│  └────────┬──────────┘                                              │           │
│           │                                                         │           │
│           ▼                                                         │           │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                           PullRequest                                      │ │
│  │ ├─ github_pr_id          ├─ merged_at           ├─ review_rounds          │ │
│  │ ├─ github_repo           ├─ first_review_at     ├─ avg_fix_response_hours │ │
│  │ ├─ title                 ├─ cycle_time_hours    ├─ commits_after_first_   │ │
│  │ ├─ author (FK) ──────────┤─ review_time_hours   │   review                │ │
│  │ ├─ state                 ├─ additions           ├─ total_comments         │ │
│  │ ├─ pr_created_at         ├─ deletions           ├─ jira_key               │ │
│  │ └─ is_revert/is_hotfix   └─ is_ai_assisted      └─ ai_tools_detected      │ │
│  └───────────────────────────────┬───────────────────────────────────────────┘ │
│                                  │                                              │
│         ┌────────────────────────┼────────────────────────────────┐            │
│         │                        │                                │            │
│         ▼                        ▼                                ▼            │
│  ┌─────────────┐         ┌─────────────┐                  ┌─────────────┐      │
│  │  PRReview   │         │   Commit    │                  │   PRFile    │      │
│  │ ├─ reviewer │         │ ├─ author   │                  │ ├─ filename │      │
│  │ ├─ state    │         │ ├─ sha      │                  │ ├─ status   │      │
│  │ └─ submitted│         │ ├─ message  │                  │ ├─ additions│      │
│  │    _at      │         │ ├─ committed│                  │ ├─ deletions│      │
│  └─────────────┘         │    _at      │                  │ └─ file_    │      │
│                          │ └─ is_ai_   │                  │    category │      │
│         ┌────────────────│    assisted │──────────────────┴─────────────┘      │
│         │                └─────────────┘                                        │
│         ▼                        │                                              │
│  ┌─────────────┐                 ▼                                              │
│  │ PRCheckRun  │         ┌─────────────┐                                        │
│  │ ├─ name     │         │  PRComment  │                                        │
│  │ ├─ status   │         │ ├─ author   │                                        │
│  │ ├─ conclusion│        │ ├─ body     │                                        │
│  │ ├─ started_at│        │ ├─ type     │                                        │
│  │ └─ duration │         │ └─ path/line│                                        │
│  └─────────────┘         └─────────────┘                                        │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐            │
│  │                      Deployment                                  │            │
│  │ ├─ github_deployment_id    ├─ environment    ├─ creator (FK)    │            │
│  │ ├─ github_repo             ├─ status         └─ sha             │            │
│  │ └─ deployed_at                                                   │            │
│  └─────────────────────────────────────────────────────────────────┘            │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐            │
│  │                      AIUsageDaily                                │            │
│  │ ├─ team_member (FK)        ├─ copilot_suggestions_accepted      │            │
│  │ ├─ date                    ├─ copilot_suggestions_rejected      │            │
│  │ └─ source                  └─ copilot_chat_turns                │            │
│  └─────────────────────────────────────────────────────────────────┘            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Member Sync

### When It Runs

| Trigger | Handler |
|---------|---------|
| After OAuth connection | `sync_github_members_task` |
| Manual refresh | Admin action |
| Periodic (optional) | Scheduled task |

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ sync_github_members()                                           │
│ apps/integrations/services/member_sync.py                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. Get organization from GitHubIntegration                      │
│        │                                                        │
│        ▼                                                        │
│ 2. Fetch org members via GitHub API                             │
│    GET /orgs/{org}/members                                      │
│        │                                                        │
│        ▼                                                        │
│ 3. For each member:                                             │
│    ┌─────────────────────────────────────────────────────────┐ │
│    │ GitHub User Data:                                        │ │
│    │ ├─ id: 12345                → github_id                  │ │
│    │ ├─ login: "developer"       → github_username            │ │
│    │ └─ name: "John Developer"   → display_name               │ │
│    └─────────────────────────────────────────────────────────┘ │
│        │                                                        │
│        ▼                                                        │
│ 4. Create/update TeamMember record                              │
│    (matched by github_id, scoped to team)                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### TeamMember Model

**Location:** `apps/metrics/models/team.py`

| Field | Source | Purpose |
|-------|--------|---------|
| `github_id` | GitHub API | Primary identifier for matching |
| `github_username` | GitHub API | Display, @ mentions |
| `display_name` | GitHub API | Human-readable name |
| `email` | GitHub API (if public) | Notifications |
| `slack_user_id` | Slack matching | DM surveys |
| `jira_account_id` | Jira matching | Issue attribution |
| `is_active` | Computed | In org membership |
| `avatar_url` | GitHub API | Profile display |

### Business Value

- **Author Attribution:** Links PRs/commits to team members
- **Reviewer Identification:** Tracks who reviews what
- **Cross-Platform Matching:** Correlates GitHub ↔ Slack ↔ Jira
- **Team Metrics:** Enables per-person dashboards

---

## Repository Tracking

### Selection Flow

```
User visits /a/{team}/integrations/github/
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ github_repos_list()                                             │
│                                                                 │
│ 1. Fetch all repos from organization via API                    │
│    GET /orgs/{org}/repos                                        │
│                                                                 │
│ 2. Display with checkboxes for selection                        │
│                                                                 │
│ 3. User toggles repos on/off                                    │
└─────────────────────────────────────────────────────────────────┘
        │
        │ User selects repo
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ toggle_repository()                                             │
│                                                                 │
│ 1. Create TrackedRepository record                              │
│ 2. Create webhook on GitHub repo                                │
│    POST /repos/{owner}/{repo}/hooks                             │
│    events: ["pull_request", "pull_request_review"]              │
│ 3. Start initial sync task                                      │
│    sync_repository_initial_task.delay(repo_id)                  │
└─────────────────────────────────────────────────────────────────┘
```

### TrackedRepository Model

**Location:** `apps/integrations/models.py`

| Field | Source | Purpose |
|-------|--------|---------|
| `full_name` | GitHub | "owner/repo" format |
| `github_repo_id` | GitHub | Webhook correlation |
| `is_active` | User toggle | Enable/disable tracking |
| `webhook_id` | GitHub | For cleanup on disable |
| `last_sync_at` | System | Incremental sync start point |
| `sync_status` | System | pending/syncing/complete/error |
| `sync_started_at` | System | Progress tracking |
| `last_sync_error` | System | Error debugging |
| `rate_limit_remaining` | GitHub | Rate limit tracking |
| `rate_limit_reset_at` | GitHub | When limit resets |

### Sync Status Flow

```
Repository Selected
        │
        ▼
    [pending]
        │
        │ sync_repository_initial_task starts
        ▼
    [syncing]
        │
        ├─── Success ───▶ [complete]
        │
        └─── Failure ───▶ [error]
                              │
                              │ Retry or manual fix
                              ▼
                          [syncing]
```

---

## Pull Request Data

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PULL REQUEST DATA FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  SOURCE 1: WEBHOOK (Real-time)                                                  │
│  ─────────────────────────────                                                  │
│                                                                                  │
│  GitHub Event: pull_request                                                      │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐        │
│  │ Webhook Payload                                                      │        │
│  │ {                                                                    │        │
│  │   "action": "closed",                                                │        │
│  │   "pull_request": {                                                  │        │
│  │     "id": 1234567890,        → github_pr_id                         │        │
│  │     "number": 42,            → (for API calls)                       │        │
│  │     "title": "Add feature",  → title, is_revert, is_hotfix, jira_key│        │
│  │     "state": "closed",       → state (combined with merged)          │        │
│  │     "merged": true,          → state = "merged"                      │        │
│  │     "merged_at": "...",      → merged_at, cycle_time_hours           │        │
│  │     "created_at": "...",     → pr_created_at                         │        │
│  │     "user": {"id": 12345},   → author (via TeamMember lookup)        │        │
│  │     "additions": 150,        → additions                             │        │
│  │     "deletions": 50,         → deletions                             │        │
│  │     "head": {"ref": "..."},  → jira_key (extracted from branch)      │        │
│  │   },                                                                 │        │
│  │   "repository": {                                                    │        │
│  │     "full_name": "owner/repo" → github_repo                          │        │
│  │   }                                                                  │        │
│  │ }                                                                    │        │
│  └─────────────────────────────────────────────────────────────────────┘        │
│       │                                                                          │
│       ▼                                                                          │
│  handle_pull_request_event() → PullRequest created/updated                      │
│       │                                                                          │
│       │ (if merged)                                                              │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐        │
│  │ Background Tasks Dispatched:                                         │        │
│  │ • send_pr_surveys_task (Slack surveys)                               │        │
│  │ • post_survey_comment_task (GitHub comment survey)                   │        │
│  │ • fetch_pr_complete_data_task (complete data fetch)                  │        │
│  └─────────────────────────────────────────────────────────────────────┘        │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  SOURCE 2: API FETCH (On merge / Historical)                                    │
│  ───────────────────────────────────────────                                    │
│                                                                                  │
│  fetch_pr_complete_data_task(pr_id)                                             │
│       │                                                                          │
│       ├──▶ sync_pr_commits()                                                    │
│       │    GET /repos/{owner}/{repo}/pulls/{number}/commits                     │
│       │    ┌────────────────────────────────────────────────────────────┐       │
│       │    │ For each commit:                                           │       │
│       │    │ • sha          → github_sha                                │       │
│       │    │ • message      → message, is_ai_assisted, ai_co_authors    │       │
│       │    │ • author.id    → author (TeamMember lookup)                │       │
│       │    │ • date         → committed_at                              │       │
│       │    │ • stats        → additions, deletions                      │       │
│       │    └────────────────────────────────────────────────────────────┘       │
│       │                                                                          │
│       ├──▶ sync_pr_files()                                                      │
│       │    GET /repos/{owner}/{repo}/pulls/{number}/files                       │
│       │    ┌────────────────────────────────────────────────────────────┐       │
│       │    │ For each file:                                             │       │
│       │    │ • filename     → filename, file_category (categorized)     │       │
│       │    │ • status       → status (added/modified/removed/renamed)   │       │
│       │    │ • additions    → additions                                 │       │
│       │    │ • deletions    → deletions                                 │       │
│       │    │ • changes      → changes                                   │       │
│       │    └────────────────────────────────────────────────────────────┘       │
│       │                                                                          │
│       ├──▶ sync_pr_check_runs()                                                 │
│       │    GET /repos/{owner}/{repo}/commits/{sha}/check-runs                   │
│       │    ┌────────────────────────────────────────────────────────────┐       │
│       │    │ For each check run:                                        │       │
│       │    │ • id           → github_check_run_id                       │       │
│       │    │ • name         → name (e.g., "pytest", "eslint")           │       │
│       │    │ • status       → status (queued/in_progress/completed)     │       │
│       │    │ • conclusion   → conclusion (success/failure/etc.)         │       │
│       │    │ • started_at   → started_at                                │       │
│       │    │ • completed_at → completed_at, duration_seconds            │       │
│       │    └────────────────────────────────────────────────────────────┘       │
│       │                                                                          │
│       ├──▶ sync_pr_issue_comments()                                             │
│       │    GET /repos/{owner}/{repo}/issues/{number}/comments                   │
│       │    ┌────────────────────────────────────────────────────────────┐       │
│       │    │ For each comment:                                          │       │
│       │    │ • id           → github_comment_id                         │       │
│       │    │ • user.id      → author (TeamMember lookup)                │       │
│       │    │ • body         → body                                      │       │
│       │    │ • created_at   → comment_created_at                        │       │
│       │    │ • updated_at   → comment_updated_at                        │       │
│       │    │ type = "issue"                                             │       │
│       │    └────────────────────────────────────────────────────────────┘       │
│       │                                                                          │
│       ├──▶ sync_pr_review_comments()                                            │
│       │    GET /repos/{owner}/{repo}/pulls/{number}/comments                    │
│       │    ┌────────────────────────────────────────────────────────────┐       │
│       │    │ For each comment:                                          │       │
│       │    │ • id           → github_comment_id                         │       │
│       │    │ • user.id      → author (TeamMember lookup)                │       │
│       │    │ • body         → body                                      │       │
│       │    │ • path         → path (file path)                          │       │
│       │    │ • line         → line (line number)                        │       │
│       │    │ • in_reply_to  → in_reply_to_id (threading)                │       │
│       │    │ type = "review"                                            │       │
│       │    └────────────────────────────────────────────────────────────┘       │
│       │                                                                          │
│       └──▶ calculate_pr_iteration_metrics(pr)                                   │
│            ┌────────────────────────────────────────────────────────────┐       │
│            │ Calculates from synced data:                               │       │
│            │ • total_comments = PRComment.count()                       │       │
│            │ • commits_after_first_review = Commit.filter(              │       │
│            │       committed_at > first_review.submitted_at).count()    │       │
│            │ • review_rounds = count(changes_requested → commit cycles) │       │
│            │ • avg_fix_response_hours = mean(commit - review times)     │       │
│            └────────────────────────────────────────────────────────────┘       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### PR Review Data Flow

```
GitHub Event: pull_request_review
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Webhook Payload                                                 │
│ {                                                               │
│   "action": "submitted",                                        │
│   "review": {                                                   │
│     "id": 456789,           → github_review_id                  │
│     "user": {"id": 54321},  → reviewer (TeamMember lookup)      │
│     "state": "approved",    → state (approved/changes_requested/│
│     "submitted_at": "...",  │         commented)                │
│     "body": "LGTM!"         → body (not currently stored)       │
│   },                                                            │
│   "pull_request": {                                             │
│     "id": 1234567890        → links to PullRequest              │
│   }                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
handle_pull_request_review_event()
       │
       ├──▶ Create/update PRReview record
       │
       └──▶ If first review: update PullRequest
            • first_review_at = submitted_at
            • review_time_hours = first_review_at - pr_created_at
```

### Business Value by Data Type

| Model | Business Value |
|-------|----------------|
| **PullRequest** | Core delivery metrics: cycle time, throughput, WIP |
| **PRReview** | Review patterns, reviewer workload, approval rates |
| **Commit** | Commit patterns, AI detection, iteration analysis |
| **PRFile** | Code distribution (frontend/backend), test coverage |
| **PRCheckRun** | CI/CD reliability, build times, failure rates |
| **PRComment** | Review thoroughness, discussion depth |

---

## Deployment Data

### Data Flow

```
sync_repository_deployments()
       │
       ▼
GET /repos/{owner}/{repo}/deployments
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ For each deployment:                                            │
│ {                                                               │
│   "id": 123456,              → github_deployment_id             │
│   "environment": "production" → environment                     │
│   "created_at": "...",       → deployed_at                      │
│   "sha": "abc123...",        → sha (commit deployed)            │
│   "creator": {"id": 12345},  → creator (TeamMember lookup)      │
│ }                                                               │
│                                                                 │
│ GET /deployments/{id}/statuses → status (pending/success/etc.)  │
└─────────────────────────────────────────────────────────────────┘
```

### Deployment Model

**Location:** `apps/metrics/models/deployment.py`

| Field | Source | Purpose |
|-------|--------|---------|
| `github_deployment_id` | GitHub | Unique identifier |
| `github_repo` | GitHub | Repository name |
| `environment` | GitHub | production/staging/etc. |
| `status` | GitHub | pending/success/failure |
| `creator` | Lookup | Who deployed |
| `deployed_at` | GitHub | Deployment timestamp |
| `sha` | GitHub | Commit that was deployed |

### Business Value

- **Deployment Frequency:** Track releases per time period
- **Lead Time:** Time from commit to production
- **Change Failure Rate:** Failed deployments / total
- **DORA Metrics:** Enable DORA research metrics

---

## Copilot Metrics

### Data Flow

```
sync_copilot_metrics_task()
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ fetch_copilot_metrics()                                         │
│ apps/integrations/services/copilot_metrics.py                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. Get org Copilot billing info                                 │
│    GET /orgs/{org}/copilot/billing                              │
│                                                                 │
│ 2. Get seat assignments                                         │
│    GET /orgs/{org}/copilot/billing/seats                        │
│                                                                 │
│ 3. Get usage metrics (if available)                             │
│    GET /orgs/{org}/copilot/usage                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ map_copilot_to_ai_usage()                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ For each user with Copilot seat:                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ AIUsageDaily record:                                        │ │
│ │ • team_member = lookup by github_id                         │ │
│ │ • date = metrics date                                       │ │
│ │ • source = "copilot"                                        │ │
│ │ • copilot_suggestions_accepted = count                      │ │
│ │ • copilot_suggestions_rejected = count                      │ │
│ │ • copilot_chat_turns = count                                │ │
│ │ • copilot_active_user = boolean                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### AIUsageDaily Model

**Location:** `apps/metrics/models/ai_usage.py`

| Field | Source | Purpose |
|-------|--------|---------|
| `team_member` | Lookup | Links to developer |
| `date` | Copilot API | Usage date |
| `source` | System | "copilot" or "survey" |
| `copilot_suggestions_accepted` | Copilot API | Accepted completions |
| `copilot_suggestions_rejected` | Copilot API | Rejected completions |
| `copilot_chat_turns` | Copilot API | Chat interactions |
| `copilot_active_user` | Copilot API | Was active on this day |

### Business Value

- **AI Adoption:** Track Copilot usage across team
- **Correlation:** Compare AI users vs non-users productivity
- **ROI Calculation:** Measure Copilot investment value

---

## Webhooks vs API Reference

### Complete Comparison Matrix

| Data Type | Webhook Event | API Endpoint | When Used |
|-----------|---------------|--------------|-----------|
| **PR Basic** | `pull_request` | `/pulls/{number}` | Webhook: real-time, API: sync |
| **PR Review** | `pull_request_review` | `/pulls/{number}/reviews` | Webhook: real-time, API: sync |
| **Commits** | ❌ None | `/pulls/{number}/commits` | API only (on merge + sync) |
| **Files** | ❌ None | `/pulls/{number}/files` | API only (on merge + sync) |
| **Check Runs** | ❌ None | `/commits/{sha}/check-runs` | API only (on merge + sync) |
| **Issue Comments** | ❌ None | `/issues/{number}/comments` | API only (on merge + sync) |
| **Review Comments** | ❌ None | `/pulls/{number}/comments` | API only (on merge + sync) |
| **Deployments** | ❌ None | `/deployments` | API only (sync) |
| **Org Members** | ❌ None | `/orgs/{org}/members` | API only (sync) |
| **Copilot Usage** | ❌ None | `/orgs/{org}/copilot/*` | API only (sync) |

### Timing Summary

| Method | Latency | Completeness | Use Case |
|--------|---------|--------------|----------|
| Webhook | ~1s | Partial (PR + reviews) | Real-time state updates |
| On-Merge Fetch | ~10-30s | Complete | Immediate complete data |
| Daily Sync | Hours | Complete | Catch missed events |
| Historical Sync | Minutes | Complete | Initial setup |

---

## Processing Summary

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        PROCESSING PIPELINE SUMMARY                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  RAW DATA                    PROCESSING                     BUSINESS VALUE      │
│  ────────                    ──────────                     ──────────────      │
│                                                                                  │
│  Webhook payload      →      _map_github_pr_to_fields()  →  PullRequest         │
│  - Extract fields            - Parse timestamps             - Cycle time        │
│  - Author ID                 - Calculate metrics            - State tracking    │
│                              - Detect flags                 - Jira correlation  │
│                                                                                  │
│  API commits          →      sync_pr_commits()           →  Commit records      │
│  - SHA, message              - Match author                 - AI detection      │
│  - Stats                     - Parse dates                  - Iteration metrics │
│                                                                                  │
│  API files            →      sync_pr_files()             →  PRFile records      │
│  - Filename, status          - Categorize file              - Code distribution │
│  - Line counts               - Extract changes              - Coverage analysis │
│                                                                                  │
│  Synced data          →      calculate_pr_iteration_     →  Updated PullRequest │
│  - Commits                     metrics()                    - review_rounds     │
│  - Reviews                   - Count cycles                 - avg_fix_response  │
│  - Comments                  - Calculate averages           - total_comments    │
│                                                                                  │
│  Copilot API          →      map_copilot_to_ai_usage()   →  AIUsageDaily        │
│  - Seat assignments          - Match to TeamMember          - AI adoption       │
│  - Usage metrics             - Aggregate daily              - Correlation data  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```
