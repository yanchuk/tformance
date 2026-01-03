# Integration Feature Flags & Coming Soon Features

**Last Updated:** 2026-01-03
**Status:** In Progress

---

## Executive Summary

Implement feature flags for Jira, Copilot, and Slack integrations to allow gradual rollout. Add Google Workspace as a "Coming Soon" feature with interest tracking. This enables:
- Control integration availability without code changes
- Track user interest in upcoming features via PostHog
- Skip disabled integrations in onboarding flow
- Show benefits of each integration even when disabled

---

## User Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Flag Scope | Global only | Team-scoped comes later |
| Button Text | "I'm Interested" | Clear call-to-action |
| Email Collection | Track only (no modal) | Simpler implementation |
| Copilot Card | Show as "Coming Soon" when flag is off | Consistent UX |

---

## User Stories

### US-1: Feature Flag Infrastructure
**As a** developer, **I want** feature flags for each optional integration **so that** we can control availability without code changes.

**Acceptance Criteria:**
- [ ] 4 waffle flags created via migration (jira, copilot, slack, google_workspace)
- [ ] `integration_flags.py` helper module with `is_integration_enabled()` function
- [ ] `get_all_integration_statuses()` returns `IntegrationStatus` dataclass
- [ ] Flags controllable via Django admin (`/admin/teams/flag/`)

### US-2: Integration Page - Disabled State
**As a** user, **I want** to see disabled integrations with benefits explanation **so that** I understand what I'm missing.

**Acceptance Criteria:**
- [ ] Show integration card even when flag is off
- [ ] Display "Coming Soon" badge
- [ ] Show benefits list (3 bullet points per integration)
- [ ] Replace Connect button with "I'm Interested" button
- [ ] Button changes to "Thanks!" after click (HTMX swap)

### US-3: Interest Tracking
**As a** product manager, **I want** to track when users click on disabled integrations **so that** I can measure demand.

**Acceptance Criteria:**
- [ ] Track `integration_interest_clicked` PostHog event
- [ ] Properties: `integration`, `team_slug`
- [ ] HTMX endpoint returns confirmation partial

### US-4: Google Workspace Coming Soon
**As a** user, **I want** to see Google Workspace as an upcoming integration.

**Acceptance Criteria:**
- [ ] Add Google Workspace card to integrations page
- [ ] Always shows "Coming Soon" (no flag check needed)
- [ ] Description: "Track communication workload in calendars"
- [ ] "I'm Interested" button with PostHog tracking

### US-5: Onboarding - Skip Disabled Integrations
**As a** user, **I want** disabled integrations skipped automatically in onboarding.

**Acceptance Criteria:**
- [ ] Check feature flag before showing Jira step
- [ ] Check feature flag before showing Slack step
- [ ] Redirect to next enabled step
- [ ] Progress indicator updates dynamically

---

## Technical Design

### New Files

| File | Purpose |
|------|---------|
| `apps/teams/migrations/0008_add_integration_flags.py` | Create 4 flags |
| `apps/integrations/services/integration_flags.py` | Flag helpers + IntegrationStatus |
| `apps/integrations/templates/integrations/components/integration_card.html` | Reusable card |
| `apps/integrations/templates/integrations/partials/interest_confirmed.html` | HTMX response |
| `apps/integrations/tests/test_integration_flags.py` | Unit tests |
| `apps/onboarding/tests/test_flag_skip.py` | Onboarding skip tests |

### Modified Files

| File | Changes |
|------|---------|
| `apps/integrations/views/status.py` | Add `track_integration_interest` view, pass flag context |
| `apps/integrations/urls.py` | Add `interest/` route |
| `apps/integrations/templates/integrations/home.html` | Use card component, add Google |
| `apps/onboarding/views.py` | Add `_get_next_onboarding_step()`, flag checks |
| `templates/onboarding/base.html` | Dynamic progress indicator |

### Flag Names

```python
FLAG_JIRA = "integration_jira_enabled"
FLAG_COPILOT = "integration_copilot_enabled"
FLAG_SLACK = "integration_slack_enabled"
FLAG_GOOGLE_WORKSPACE = "integration_google_workspace_enabled"
```

### IntegrationStatus Dataclass

```python
@dataclass
class IntegrationStatus:
    name: str           # "Jira"
    slug: str           # "jira"
    enabled: bool       # Flag is on
    coming_soon: bool   # Show Coming Soon badge
    icon_class: str     # "fa-brands fa-jira"
    icon_color: str     # "text-blue-500"
    description: str    # Short description
    benefits: list[dict]  # [{title, description}, ...]
```

### HTMX Interest Tracking Flow

```
[I'm Interested] --POST--> /integrations/interest/?integration=jira
                              |
                              v
                        track_event(user, "integration_interest_clicked", {...})
                              |
                              v
                  return partials/interest_confirmed.html
                              |
                              v
                    [Thanks!] (disabled button)
```

---

## Implementation Phases

### Phase 1: Flag Infrastructure (S - 1hr)
1. Write failing tests for flag helpers
2. Create migration with 4 flags
3. Create `integration_flags.py` with helper functions
4. Run migration, verify tests pass

### Phase 2: Integration Page UI (M - 2hr)
1. Write failing tests for integration page with flag context
2. Create `integration_card.html` component
3. Update `integrations_home` view to pass flag context
4. Update `home.html` to use component
5. Add Google Workspace card
6. Style Coming Soon state

### Phase 3: Interest Tracking (S - 1hr)
1. Write failing tests for interest tracking endpoint
2. Add `track_integration_interest` view
3. Add URL route
4. Create `interest_confirmed.html` partial
5. Verify tests pass

### Phase 4: Onboarding Flow (M - 2hr)
1. Write failing tests for onboarding skip logic
2. Add `_get_next_onboarding_step()` helper
3. Update `connect_jira` view with flag check
4. Update `connect_slack` view with flag check
5. Verify tests pass

### Phase 5: E2E Testing & Polish (S - 1hr)
1. Write Playwright tests for disabled states
2. Test all flows end-to-end
3. Verify PostHog events in browser

---

## Integration Benefits Content

### Jira
- **Sprint velocity**: Track story points delivered per sprint
- **Issue cycle time**: Measure time from start to done
- **PR-to-issue linking**: Connect code changes to business outcomes

### GitHub Copilot
- **Acceptance rate**: Track how often suggestions are accepted
- **Lines of code**: Measure AI-generated code volume
- **Time savings**: Estimate productivity gains from AI

### Slack
- **PR surveys via DM**: Quick 1-click surveys to capture AI-assisted PRs
- **Weekly leaderboards**: Gamified AI Detective rankings
- **Higher response rates**: Meet developers where they work

### Google Workspace
- **Meeting time analysis**: Track time spent in meetings vs coding
- **Focus time patterns**: Identify optimal deep work windows
- **Team availability**: Optimize collaboration windows

---

## Onboarding Flow Logic

```
sync_progress → [jira if enabled] → [slack if enabled] → complete

_get_next_onboarding_step(request, current_step):
    if current == "sync_progress":
        if jira_enabled: return "jira"
        elif slack_enabled: return "slack"
        else: return "complete"

    if current == "jira":
        if slack_enabled: return "slack"
        else: return "complete"

    if current == "slack":
        return "complete"
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Flag migration fails | High | Test in staging first |
| Breaking existing integration pages | High | TDD approach ensures coverage |
| PostHog events not tracked | Low | Add E2E test verification |
| Onboarding flow breaks | High | Comprehensive test coverage |

---

## Success Metrics

1. All 4 flags created and controllable via admin
2. Integration page shows Coming Soon state correctly
3. PostHog receives `integration_interest_clicked` events
4. Onboarding correctly skips disabled integrations
5. All unit and E2E tests pass
