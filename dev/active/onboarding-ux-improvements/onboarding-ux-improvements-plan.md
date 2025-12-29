# Onboarding UX Improvements - Implementation Plan

**Last Updated:** 2025-12-29

## Executive Summary

Comprehensive improvements to the Tformance onboarding flow based on senior PM/UX review. Addresses 22 identified issues across P0-P3 priorities, plus 3 missing features from PRD documentation.

**Scope:** Full implementation using TDD methodology
**Estimated Total Effort:** 3-4 days

---

## Current State Analysis

### Existing Flow
```
Signup → GitHub Connect → Org Select → Repo Select → Sync Progress → Jira → Slack → Complete
```

### Key Files
- `templates/account/signup.html` - Signup page
- `templates/onboarding/base.html` - Base layout with progress indicator
- `templates/onboarding/start.html` - GitHub connection start
- `templates/onboarding/select_org.html` - Organization selection
- `templates/onboarding/select_repos.html` - Repository selection
- `templates/onboarding/sync_progress.html` - Sync status
- `templates/onboarding/connect_jira.html` - Jira connection
- `templates/onboarding/connect_slack.html` - Slack connection
- `templates/onboarding/complete.html` - Completion page
- `apps/onboarding/views.py` - View logic
- `apps/integrations/services/sync_notifications.py` - Email infrastructure

### Existing Infrastructure
- Email templates: `templates/account/email/email_template_base.html`
- Sync notification service exists but only for repo sync complete
- Alpine.js and HTMX already integrated

---

## Proposed Future State

### UX Improvements
1. Clear password requirements shown during signup
2. Accurate time estimates throughout onboarding
3. Visual distinction between required (GitHub, Repos) and optional (Jira, Slack) steps
4. Positive completion messaging without false "incomplete" indicators
5. Repository search/filter for large organizations
6. Loading states and error recovery on all OAuth buttons
7. Mobile-responsive step indicators
8. Celebration animation at completion

### New Features
1. Welcome email sent after team creation
2. Sync complete email notification
3. Slack configuration form during onboarding

---

## Implementation Phases

### Phase 1: P0 Critical Fixes (Template-Only)
**Effort:** S (2-3 hours)

These are template-only changes with no backend logic.

| Task | File | Description |
|------|------|-------------|
| 1.1 | `signup.html` | Add password requirements hint |
| 1.2 | `signup.html` | Add Privacy Policy link |
| 1.3 | `base.html` | Add "(optional)" labels to Jira/Slack steps |
| 1.4 | `base.html` | Add time estimate "~5 min" |
| 1.5 | `complete.html` | Change warning icons to info icons |
| 1.6 | `complete.html` | Update copy for skipped integrations |

### Phase 2: P1 High Priority (Template + Alpine.js)
**Effort:** M (1 day)

| Task | File | Description |
|------|------|-------------|
| 2.1 | `select_repos.html` | Add search input with Alpine.js filter |
| 2.2 | `select_repos.html` | Add "Recently Active" badge |
| 2.3 | `select_repos.html` | Auto-select top 5 active repos |
| 2.4 | `connect_jira.html` | Fix button hierarchy (connect=primary) |
| 2.5 | `connect_slack.html` | Fix button hierarchy (connect=primary) |
| 2.6 | `sync_progress.html` | Make continue button more prominent |
| 2.7 | `start.html` | Add info tooltip for permissions |

### Phase 3: P2 Medium Priority (Template + CSS)
**Effort:** M (1 day)

| Task | File | Description |
|------|------|-------------|
| 3.1 | `base.html` | Add progress persistence indicator |
| 3.2 | `base.html` | Enhance floating sync indicator |
| 3.3 | `base.html` | Mobile responsive step indicator |
| 3.4 | `design-system.css` | Add focus states for interactive cards |

### Phase 4: P3 Low Priority + Missing Features
**Effort:** L (1-2 days)

| Task | File | Description |
|------|------|-------------|
| 4.1 | All OAuth templates | Add loading states to buttons |
| 4.2 | All templates | Add error recovery CTAs |
| 4.3 | `complete.html` | Add celebration animation |
| 4.4 | `complete.html` | Add personalized welcome |
| 4.5 | New service | Implement welcome email |
| 4.6 | Existing service | Implement sync complete email |
| 4.7 | `connect_slack.html` | Add Slack configuration form |

---

## Technical Specifications

### 1. Password Requirements Hint
```html
<p class="text-xs text-base-content/60 mt-1">
  Minimum 8 characters with at least one number
</p>
```

### 2. Optional Step Labels
```html
<span class="app-step-label {% if step >= 3 %}app-step-label-active{% endif %}">
  {% translate "Jira" %}
  <span class="text-xs text-base-content/50 block">(optional)</span>
</span>
```

### 3. Repository Search Filter (Alpine.js)
```javascript
x-data="{
  searchQuery: '',
  selectedRepos: [],
  get filteredRepos() {
    if (!this.searchQuery) return this.allRepos;
    return this.allRepos.filter(r =>
      r.name.toLowerCase().includes(this.searchQuery.toLowerCase())
    );
  }
}"
```

### 4. Welcome Email Service
```python
# apps/onboarding/services/notifications.py
def send_welcome_email(team: Team, user: CustomUser) -> bool:
    """Send welcome email after team creation."""
    context = {
        'name': user.first_name or 'there',
        'team_name': team.name,
        'dashboard_url': f"{settings.BASE_URL}/a/{team.slug}/",
    }
    # Use existing email template infrastructure
```

### 5. Slack Configuration Form Fields
Per PRD ONBOARDING.md (lines 182-200):
- Channel selector (dropdown)
- Schedule day picker
- Schedule time picker
- Feature toggles: surveys, leaderboard, reveal messages

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Template changes break existing styling | Medium | Test in light/dark themes |
| Email delivery issues | Low | Use existing email infrastructure |
| Mobile responsiveness issues | Medium | Test on multiple screen sizes |
| Alpine.js conflicts | Low | Isolate x-data scopes |

---

## Success Metrics

1. **Signup completion rate** - Target: +10% improvement
2. **Onboarding completion rate** - Target: +15% improvement
3. **Time to first dashboard** - Target: Accurate ~5 min expectation set
4. **User satisfaction** - Post-onboarding survey (future)

---

## Test Requirements (TDD)

Each phase requires tests written BEFORE implementation:

### Phase 1 Tests
- Template rendering tests for new elements
- Password hint visibility test
- Privacy policy link presence test

### Phase 2 Tests
- Alpine.js repo filter functionality
- Button hierarchy validation
- Tooltip content verification

### Phase 3 Tests
- Mobile breakpoint tests (Playwright)
- Focus state accessibility tests

### Phase 4 Tests
- Email service unit tests
- Email template rendering tests
- Slack config form validation tests

---

## Dependencies

- No new packages required
- Existing Alpine.js (v3.x)
- Existing email infrastructure (Django send_mail)
- Existing email templates

---

## Implementation Order

```
Phase 1 (P0) → Phase 2 (P1) → Phase 3 (P2) → Phase 4 (P3)
     ↓             ↓             ↓             ↓
  Tests        Tests        Tests        Tests
     ↓             ↓             ↓             ↓
  Implement   Implement    Implement    Implement
     ↓             ↓             ↓             ↓
  Verify      Verify       Verify       Verify
```

Each phase is independently deployable.
