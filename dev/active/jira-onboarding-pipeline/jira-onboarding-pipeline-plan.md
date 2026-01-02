# Jira Onboarding Pipeline - Implementation Plan

**Last Updated**: 2026-01-01
**Status**: Ready for Implementation
**Related**: `dev/active/two-phase-onboarding/`
**Approach**: Strict TDD (Red-Green-Refactor)

---

## Executive Summary

When users connect Jira and select projects during onboarding, projects are created with `sync_status=PENDING` and wait for the daily Celery beat job (up to 24 hours). This creates a poor first-run experience where Jira data is missing from insights.

**Solution**: Add a parallel Jira onboarding pipeline that triggers immediately after project selection, syncs users and issues, and provides Jira metrics to insights.

---

## Current State Analysis

### What Works
- GitHub two-phase pipeline syncs repos immediately during onboarding
- Jira OAuth connection works correctly
- `TrackedJiraProject` model tracks selected projects
- `sync_project_issues()` and `sync_jira_users()` services exist
- Dashboard already checks for "missing Jira link" on PRs

### What's Broken
1. **No immediate sync** - `select_jira_projects` creates records but doesn't trigger sync
2. **No user matching** - `sync_jira_users_task` never called during onboarding
3. **No insights** - Jira data exists but isn't used in `gather_insight_data()`
4. **No progress UI** - User has no visibility into Jira sync status

---

## Proposed Future State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ONBOARDING FLOW (After Fix)                         │
└─────────────────────────────────────────────────────────────────────────────┘

User selects GitHub repos
        │
        ▼
┌─────────────────────┐
│ GitHub Phase 1      │ ──────────────────────────────────────────┐
│ (30 days + LLM)     │                                           │
└─────────────────────┘                                           │
        │                                                          │
        ▼                                                          │
User selects Jira projects
        │
        ▼
┌─────────────────────┐    ┌─────────────────────┐                │
│ Jira Pipeline       │    │ GitHub Phase 2      │ ◄──────────────┘
│ (users + issues)    │    │ (31-90 days)        │  (background)
└─────────────────────┘    └─────────────────────┘
        │                          │
        ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Dashboard Ready                               │
│  - GitHub metrics (Phase 1 data)                                │
│  - Jira correlation (sprint metrics, PR linkage)                │
│  - Insights include Jira data                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Pipeline Type** | Parallel (not in GitHub chain) | Jira is optional, shouldn't block GitHub |
| **UI Feedback** | Inline indicator | Don't block navigation to Slack step |
| **Error Handling** | Silent retry | Log error, retry in nightly batch |
| **Insights Scope** | Include in this work | Full value requires Jira metrics |

---

## Implementation Phases

### Phase 1: Core Pipeline (TDD)
Build the Celery pipeline infrastructure with strict TDD.

| Task | Effort | Description |
|------|--------|-------------|
| 1.1 | S | Write failing tests for `sync_jira_users_onboarding` task |
| 1.2 | S | Implement `sync_jira_users_onboarding` to pass tests |
| 1.3 | S | Write failing tests for `sync_jira_projects_onboarding` task |
| 1.4 | M | Implement `sync_jira_projects_onboarding` to pass tests |
| 1.5 | S | Write failing tests for `start_jira_onboarding_pipeline` chain |
| 1.6 | S | Implement `start_jira_onboarding_pipeline` to pass tests |
| 1.7 | S | Refactor: Extract common patterns, improve error handling |

### Phase 2: View Integration (TDD)
Connect pipeline to onboarding views.

| Task | Effort | Description |
|------|--------|-------------|
| 2.1 | S | Write failing tests for pipeline trigger in `select_jira_projects` |
| 2.2 | M | Modify `select_jira_projects` to trigger pipeline on POST |
| 2.3 | S | Write failing tests for `jira_sync_status` endpoint |
| 2.4 | M | Implement `jira_sync_status` view and URL |
| 2.5 | S | Add URL pattern to `apps/onboarding/urls.py` |
| 2.6 | S | Refactor: Clean up view logic, add logging |

### Phase 3: Jira Metrics (TDD)
Add Jira data to dashboard service.

| Task | Effort | Description |
|------|--------|-------------|
| 3.1 | S | Write failing tests for `get_jira_sprint_metrics` |
| 3.2 | M | Implement `get_jira_sprint_metrics` to pass tests |
| 3.3 | S | Write failing tests for `get_pr_jira_correlation` |
| 3.4 | M | Implement `get_pr_jira_correlation` to pass tests |
| 3.5 | S | Refactor: Optimize queries, add edge case handling |

### Phase 4: Insights Integration (TDD)
Wire Jira metrics into insight generation.

| Task | Effort | Description |
|------|--------|-------------|
| 4.1 | S | Write failing tests for Jira in `gather_insight_data` |
| 4.2 | M | Modify `gather_insight_data` to include Jira metrics |
| 4.3 | S | Update prompt template with Jira section |
| 4.4 | S | Refactor: Test template rendering, handle None values |

### Phase 5: UI Polish
Add inline progress indicator.

| Task | Effort | Description |
|------|--------|-------------|
| 5.1 | M | Add Alpine.js progress indicator to `select_jira_projects.html` |
| 5.2 | S | Add session storage flag for sync started |
| 5.3 | S | Test polling behavior and status transitions |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Jira API rate limits | Medium | Medium | Use batch API calls, respect 429s |
| Long sync for large projects | Medium | Low | Background sync, don't block UI |
| User matching failures | Low | Low | Continue sync, log unmatched users |
| Celery task failures | Low | Medium | Silent retry in nightly batch |

---

## Success Metrics

- [ ] Jira sync starts within 1 second of project selection
- [ ] `JiraIssue` records created within 1-2 minutes
- [ ] `TeamMember.jira_account_id` populated for matched users
- [ ] Insights include Jira sprint metrics when connected
- [ ] Insights show PR-Jira linkage rate
- [ ] Inline progress indicator shows sync status
- [ ] All tests pass (100% coverage on new code)
- [ ] No user-facing errors on sync failure

---

## Dependencies

### External
- Jira API (Atlassian Cloud)
- Celery + Redis (for task queue)

### Internal
- `apps/integrations/services/jira_sync.py` - existing sync logic
- `apps/integrations/services/jira_user_matching.py` - user matching
- `apps/metrics/services/dashboard_service.py` - metrics gathering
- `apps/metrics/services/insight_llm.py` - insight generation

---

## Rollout Plan

1. **No migration required** - uses existing models
2. **Backward compatible** - existing teams unaffected
3. **Feature flag (optional)** - `waffle.flag("jira_onboarding_pipeline")`
4. **Monitoring** - Add Sentry breadcrumbs for pipeline stages
