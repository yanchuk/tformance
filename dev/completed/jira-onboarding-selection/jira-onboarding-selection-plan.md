# Plan: Jira Project Selection in Onboarding

**Last Updated: 2025-12-28**

## Executive Summary

Implement Jira project selection as Step 4 of the onboarding flow. Users connect their Jira account via OAuth and select which Jira projects to track. This mirrors the GitHub repository selection pattern but is implemented directly in onboarding (unlike GitHub which shows a placeholder).

## Current State Analysis

### Onboarding Flow (Current)
1. **Start** → Connect GitHub button
2. **GitHub OAuth** → Unified auth callback
3. **Select Organization** → Creates Team
4. **Select Repositories** → Placeholder ("coming soon")
5. **Connect Jira** → **DISABLED** (shows "Coming Soon" badge)
6. **Connect Slack** → Optional
7. **Complete** → Dashboard

### Jira Infrastructure (Existing)
| Component | Status | Location |
|-----------|--------|----------|
| `JiraIntegration` model | ✅ Exists | `apps/integrations/models.py:283` |
| `TrackedJiraProject` model | ✅ Exists | `apps/integrations/models.py:346` |
| Jira OAuth service | ✅ Exists | `apps/integrations/services/jira_oauth.py` |
| Jira client (jira-python) | ✅ Exists | `apps/integrations/services/jira_client.py` |
| `jira_projects_list` view | ✅ Basic | `apps/integrations/views/jira.py:215` |
| `jira_project_toggle` view | ✅ Complete | `apps/integrations/views/jira.py:262` |
| Onboarding Jira view | ❌ Disabled | `apps/onboarding/views.py:connect_jira` |

### What's Missing
1. Jira OAuth state with onboarding flow type
2. Onboarding-specific Jira project selection view
3. Template for Jira project selection in onboarding
4. Routing from Jira OAuth callback to onboarding flow
5. "Select All" / "Deselect All" functionality

## Proposed Future State

### Updated Onboarding Flow
1. Start → Connect GitHub
2. GitHub OAuth → Callback routes to onboarding
3. Select Organization → Creates Team
4. Select Repositories → (Placeholder - future work)
5. **Connect Jira** → **ENABLED** - Initiates Jira OAuth
6. **Select Jira Projects** → **NEW** - Checkbox selection with "Select All"
7. Connect Slack → Optional
8. Complete → Dashboard

### User Experience
```
┌─────────────────────────────────────────────────────────┐
│              Select Jira Projects                        │
│  Which projects should tformance track?                  │
│                                                          │
│  [☑ Select All]                                         │
│                                                          │
│  ☑️ ACME - Main Product                                  │
│     Software project • 234 issues                        │
│                                                          │
│  ☑️ API - API Development                                │
│     Software project • 156 issues                        │
│                                                          │
│  ☐ OPS - Internal Operations                             │
│     Service project • 89 issues                          │
│                                                          │
│  ☐ HR - Human Resources                                  │
│     Business project • 45 issues                         │
│                                                          │
│           [← Back]  [Continue →]                         │
│                                                          │
│  ℹ️ You can change these later in Settings               │
└─────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: OAuth State Infrastructure
- Add `FLOW_TYPE_JIRA_ONBOARDING` to auth OAuth state module
- Update Jira OAuth to use unified state management
- Ensure callback can distinguish onboarding vs integration flows

### Phase 2: Enable Jira Connection in Onboarding
- Update `connect_jira` view to initiate OAuth
- Remove "Coming Soon" badge from template
- Wire OAuth callback to route to project selection

### Phase 3: Implement Project Selection View
- Create `select_jira_projects` view in onboarding
- Fetch projects via `jira_client.get_accessible_projects()`
- Handle GET (display) and POST (save selections)
- Support "Select All" functionality

### Phase 4: Create Project Selection Template
- Design template following onboarding patterns
- Checkbox list with project details
- Alpine.js for "Select All" toggle
- HTMX for smooth interactions

### Phase 5: Testing
- Unit tests for new views
- Integration tests for OAuth flow
- E2E tests for complete onboarding with Jira

## Architecture Decision

**Decision**: Implement project selection directly in onboarding (not placeholder like GitHub repos)

**Rationale**:
1. Jira project selection is simpler than repo selection (fewer projects, no webhooks)
2. Projects are typically fewer (<20) vs repositories (can be hundreds)
3. No webhook creation needed (unlike GitHub)
4. Better user experience to complete setup in one flow

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Jira OAuth token expiry mid-flow | Low | Medium | Use `ensure_valid_jira_token()` |
| Multiple Jira sites | Low | Low | Already handled in `jira_select_site` |
| No projects returned | Low | Low | Show helpful message, allow skip |
| Rate limiting | Very Low | Low | Jira API is generous |

## Success Metrics

- [ ] User can connect Jira in onboarding
- [ ] User sees list of accessible Jira projects
- [ ] User can select/deselect individual projects
- [ ] User can "Select All" / "Deselect All"
- [ ] Selected projects create `TrackedJiraProject` records
- [ ] Flow continues to Slack step after selection
- [ ] All tests pass
