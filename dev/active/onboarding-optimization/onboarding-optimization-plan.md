# Onboarding Flow Optimization Plan

**Last Updated:** 2025-12-28

## Executive Summary

Optimize the GitHub integration onboarding flow to display actionable insights as fast as possible. Current time-to-first-insight is 10-30 minutes; target is <2 minutes.

**Core Objective:** When a user connects their GitHub org and selects repos, they should see meaningful dashboard data within 2 minutes, not wait 10+ minutes for a complete historical sync.

---

## Current State Analysis

### Current Flow Timeline

```
Step 1: OAuth Callback (10-30s for large orgs)
├── Exchange code for token (1s)
├── Fetch user orgs (1s)
├── Create Team + GitHubIntegration (instant)
└── BLOCKING: sync_github_members() (10-30s for 100+ members)
    └── For each member: get_user_details() API call

Step 2: Repository Selection (2-10s)
├── GET: Fetch all org repos (2-5s)
├── User selects repos
└── POST: For each selected repo:
    ├── Create TrackedRepository (instant)
    ├── Create webhook (API call) - BLOCKING
    └── Queue sync_repository_initial_task (Celery)

Step 3: Historical Sync (5-30 minutes) - BACKGROUND
├── Default: 30 days of PR history
├── For each PR:
│   ├── Fetch reviews, commits, files, comments, check runs
│   └── Run LLM analysis (0.5-2s per PR) - SLOW
└── Post-sync: Aggregate weekly metrics

Step 4: Dashboard (EMPTY until sync complete)
└── Requires: PRs with merged_at, cycle time, AI detection data
```

### Identified Bottlenecks

| Priority | Issue | Location | Impact |
|----------|-------|----------|--------|
| **P0** | Member sync blocks OAuth | `apps/auth/views.py:181-185` | 10-30s delay |
| **P0** | Redirect skips sync progress | `apps/onboarding/views.py:271` | User confusion |
| **P0** | 30-day sync too long | `sync_repository_initial_task` | 5-15 min wait |
| **P1** | LLM analysis during sync | `OnboardingSyncService` | +0.5-2s per PR |
| **P1** | Dashboard empty until done | `templates/web/app_home.html` | Bad UX |
| **P2** | Webhook creation blocking | `github_repo_toggle` view | N*1s delay |
| **P2** | No repo prioritization | All repos equal | Slow for active repos |

---

## Proposed Future State

### Optimized Flow Timeline

```
Step 1: OAuth Callback (<3s total)
├── Exchange code for token (1s)
├── Fetch user orgs (1s)
├── Create Team + GitHubIntegration (instant)
└── ASYNC: Queue sync_github_members_task()  ← NEW

Step 2: Repository Selection (<5s)
├── GET: Fetch all org repos (2-3s)
├── User selects repos (prioritized by activity)
└── POST: For each selected repo:
    ├── Create TrackedRepository (instant)
    └── ASYNC: Queue webhook creation  ← NEW

Step 3: Redirect to Sync Progress Page  ← NEW
└── Show real-time progress

Step 4: Two-Phase Sync  ← NEW
├── Phase A: Quick Sync (7 days, no LLM) - ~60 seconds
│   ├── Pattern detection only (instant)
│   ├── Aggregate quick metrics
│   └── Enable dashboard with partial data
│
└── Phase B: Full Sync (90 days, with LLM) - Background
    ├── Continue fetching historical data
    ├── Run LLM batch analysis
    └── Progressively enhance dashboard

Step 5: Progressive Dashboard  ← NEW
├── Shows available data immediately
├── "Syncing..." indicator with progress
├── Updates as more data arrives
└── Full view when complete
```

### Target Metrics

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| OAuth callback time | 10-30s | <3s | 90% faster |
| Time to first PR visible | 5-15 min | <90s | 10x faster |
| Time to dashboard insights | 10-30 min | <2 min | 15x faster |
| User sees sync progress | Sometimes | Always | 100% visibility |

---

## Implementation Phases

### Phase 1: Quick Wins (Effort: S, Impact: High)

**Goal:** Remove blocking operations and improve UX without major refactoring.

#### 1.1 Async Member Sync
- **What:** Queue member sync as Celery task instead of blocking OAuth
- **Files:** `apps/auth/views.py`, `apps/onboarding/views.py`
- **Effort:** S (30 min)
- **Impact:** OAuth <3s instead of 10-30s

#### 1.2 Redirect to Sync Progress
- **What:** After repo selection, show sync progress page
- **Files:** `apps/onboarding/views.py`
- **Effort:** S (15 min)
- **Impact:** User sees their data syncing

#### 1.3 Continue in Background Option
- **What:** Add button to continue to Jira while sync runs
- **Files:** `templates/onboarding/sync_progress.html`
- **Effort:** S (1 hour)
- **Impact:** User not blocked by long sync

---

### Phase 2: Two-Phase Sync (Effort: M, Impact: High)

**Goal:** Implement quick sync (7 days) + deferred full sync pattern.

#### 2.1 Create Quick Sync Task
- **What:** New Celery task that syncs only 7 days of data
- **Files:** `apps/integrations/tasks.py`, new `services/quick_sync.py`
- **Effort:** M (3 hours)
- **Dependencies:** None

#### 2.2 Pattern Detection Only (Skip LLM)
- **What:** Use regex AI detection for quick sync, defer LLM
- **Files:** `apps/integrations/services/onboarding_sync.py`
- **Effort:** S (1 hour)
- **Dependencies:** 2.1

#### 2.3 Immediate Metrics Aggregation
- **What:** Run weekly metrics after quick sync completes
- **Files:** `apps/integrations/tasks.py`
- **Effort:** S (30 min)
- **Dependencies:** 2.1

#### 2.4 Queue Full Sync
- **What:** After quick sync, queue full 90-day sync in background
- **Files:** `apps/integrations/tasks.py`
- **Effort:** S (30 min)
- **Dependencies:** 2.1

#### 2.5 Deferred LLM Batch Task
- **What:** New task to run LLM on PRs without analysis
- **Files:** `apps/integrations/tasks.py`
- **Effort:** M (2 hours)
- **Dependencies:** 2.4

---

### Phase 3: Progressive Dashboard (Effort: M, Impact: Medium)

**Goal:** Show partial data immediately, enhance as sync progresses.

#### 3.1 Sync Status in Dashboard Context
- **What:** Add sync progress to dashboard view context
- **Files:** `apps/web/views.py`, `apps/integrations/services/status.py`
- **Effort:** S (1 hour)
- **Dependencies:** 2.1

#### 3.2 Dashboard Sync Indicator UI
- **What:** Show "syncing" banner with progress in dashboard
- **Files:** `templates/web/app_home.html`
- **Effort:** S (1 hour)
- **Dependencies:** 3.1

#### 3.3 Partial Data Display
- **What:** Show available stats even if sync incomplete
- **Files:** `apps/metrics/services/quick_stats.py`
- **Effort:** M (2 hours)
- **Dependencies:** 3.1

#### 3.4 First Insights Ready Banner
- **What:** Notification when quick sync completes
- **Files:** `templates/onboarding/sync_progress.html`
- **Effort:** S (1 hour)
- **Dependencies:** 2.1

---

### Phase 4: UX Polish (Effort: S, Impact: Low-Medium)

**Goal:** Final polish for smooth experience.

#### 4.1 Repository Prioritization
- **What:** Sort repos by recent activity in selection UI
- **Files:** `apps/onboarding/views.py`
- **Effort:** S (1 hour)
- **Dependencies:** None

#### 4.2 Async Webhook Creation
- **What:** Queue webhook creation instead of blocking
- **Files:** `apps/integrations/views/github.py`, `tasks.py`
- **Effort:** S (1 hour)
- **Dependencies:** None

#### 4.3 Estimated Time Display
- **What:** Show "~2 minutes remaining" in progress
- **Files:** `templates/onboarding/sync_progress.html`
- **Effort:** S (30 min)
- **Dependencies:** 2.1

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Quick sync data insufficient | Medium | Medium | 7 days is enough for initial insights; full sync follows |
| Pattern detection inaccurate | Low | Low | LLM results appear later; 85%+ accuracy from patterns |
| Members missing from PRs | Medium | Low | Author can be NULL; daily sync fixes it |
| Race condition in two-phase sync | Low | Medium | Use atomic status updates; test thoroughly |

---

## Success Metrics

### Primary KPIs
- Time to first dashboard data: <2 minutes (currently 10-30 min)
- OAuth callback completion: <3 seconds (currently 10-30s)
- User sees sync progress: 100% (currently inconsistent)

### Secondary KPIs
- Onboarding completion rate: Track before/after
- Time spent on sync progress page: Should decrease
- Support tickets about "no data": Should decrease

---

## Dependencies

### External
- GitHub API rate limits (5000/hour with token)
- Celery worker capacity
- Redis for task queue

### Internal
- `apps/integrations/tasks.py` - All sync tasks
- `apps/metrics/models.py` - PullRequest model
- `apps/integrations/services/` - Sync services

---

## Implementation Order

```
Week 1 (Quick Wins):
├── 1.1 Async member sync
├── 1.2 Redirect to sync progress
└── 1.3 Continue in background button

Week 2 (Two-Phase Sync):
├── 2.1 Quick sync task
├── 2.2 Pattern detection only
├── 2.3 Immediate metrics aggregation
├── 2.4 Queue full sync
└── 2.5 Deferred LLM batch

Week 3 (Progressive Dashboard):
├── 3.1 Sync status in context
├── 3.2 Dashboard sync indicator
├── 3.3 Partial data display
└── 3.4 First insights banner

Week 4 (Polish):
├── 4.1 Repo prioritization
├── 4.2 Async webhook creation
└── 4.3 Estimated time display
```

---

## Testing Strategy

### Unit Tests
- Quick sync task creates correct data
- Pattern detection matches LLM for common cases
- Metrics aggregation works with partial data

### Integration Tests
- Full onboarding flow with async operations
- Two-phase sync completes successfully
- Dashboard updates as sync progresses

### E2E Tests
- User can see dashboard data within 2 minutes of connecting
- Progress indicators work correctly
- Continue in background doesn't break flow

---

## Rollback Plan

Each phase can be rolled back independently:
1. **Phase 1:** Revert to synchronous member sync (feature flag)
2. **Phase 2:** Disable quick sync, use single-phase sync
3. **Phase 3:** Hide sync indicators, show "loading" state
4. **Phase 4:** Non-critical, skip entirely if needed
