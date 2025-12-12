# MVP Feature Review & UI Audit Plan

**Last Updated:** 2025-12-13

## Executive Summary

Comprehensive review of all MVP functionality (Phases 0-7) to verify implementation completeness, test coverage, and UI quality. This audit will use the frontend-design skill for UI evaluation and ensure all features work end-to-end.

**Goal:** Verify MVP is production-ready by systematically testing every feature and UI flow.

---

## Current State Analysis

### Completed Phases (from dev/completed/)

| Phase | Implementation | Status |
|-------|---------------|--------|
| 0. Foundation | Auth, Teams, Secrets | Complete |
| 1. Core Models | TeamMember, PR, Jira, Survey models | Complete |
| 2. GitHub | OAuth, Org Discovery, Repos, Webhooks, Sync | Complete |
| 3. Jira | OAuth, Projects, User Matching, Sync | Complete |
| 4. Dashboard | Chart.js, HTMX lazy loading, CTO/Team views | Complete |
| 5. Slack | OAuth, Surveys, Reveals | Complete |
| 6. AI Correlation | AI adoption/quality charts | Complete |
| 7. Leaderboard | Weekly aggregation, Slack posting | Complete |

### Key URLs to Review

**Public:**
- `/` - Landing page
- `/accounts/login/` - Login
- `/accounts/signup/` - Signup
- `/onboarding/` - Onboarding flow

**Authenticated (team context):**
- `/app/` - App home / redirect
- `/app/dashboard/cto/` - CTO Overview
- `/app/dashboard/team/` - Team Dashboard
- `/app/integrations/` - Integrations management
- `/app/team/` - Team settings

---

## Review Sections

### Section 1: Authentication & Accounts

**Scope:** User registration, login, team creation

| Test | Expected Behavior | Priority |
|------|------------------|----------|
| 1.1 Sign up flow | Create account, verify email (if enabled) | High |
| 1.2 Login flow | Login with email/password | High |
| 1.3 Logout | Session cleared, redirect to home | High |
| 1.4 Team creation | Create new team during signup | High |
| 1.5 Team switching | Switch between teams (if multiple) | Medium |
| 1.6 Password reset | Request reset, receive email | Medium |

**UI Audit Points:**
- Form styling consistency (DaisyUI inputs)
- Error message display
- Loading states
- Mobile responsiveness

---

### Section 2: Onboarding Flow

**Scope:** `/onboarding/` step-by-step wizard

| Test | Expected Behavior | Priority |
|------|------------------|----------|
| 2.1 Start onboarding | Show step 1 (GitHub connect) | High |
| 2.2 GitHub OAuth | Redirect to GitHub, return with token | High |
| 2.3 Org selection | List orgs, select one | High |
| 2.4 Repo selection | List repos, toggle tracked | High |
| 2.5 Jira connect (optional) | OAuth flow or skip | Medium |
| 2.6 Slack connect (optional) | OAuth flow or skip | Medium |
| 2.7 Complete | Redirect to dashboard | High |

**UI Audit Points:**
- Progress indicator styling
- Step transitions (HTMX)
- Skip button visibility
- Success/error states

---

### Section 3: Integrations Management

**Scope:** `/app/integrations/`

| Test | Expected Behavior | Priority |
|------|------------------|----------|
| 3.1 Integrations home | Show connected/disconnected status | High |
| 3.2 GitHub connect/disconnect | Toggle connection | High |
| 3.3 GitHub members page | List members, toggle tracking | High |
| 3.4 GitHub repos page | List repos, toggle tracking, trigger sync | High |
| 3.5 Jira connect/disconnect | Toggle connection | High |
| 3.6 Jira site selection | Select Atlassian site | Medium |
| 3.7 Jira projects page | List projects, toggle tracking | High |
| 3.8 Slack connect/disconnect | Toggle connection | High |
| 3.9 Slack settings | Configure leaderboard channel/schedule | Medium |

**UI Audit Points:**
- Integration cards layout
- Connected vs disconnected states
- Member/repo list tables
- Toggle switches functionality
- Sync status indicators

---

### Section 4: CTO Dashboard

**Scope:** `/app/dashboard/cto/`

| Test | Expected Behavior | Priority |
|------|------------------|----------|
| 4.1 Dashboard loads | All chart containers render | High |
| 4.2 Key metrics cards | PRs, Cycle Time, Quality, AI % | High |
| 4.3 AI Adoption chart | Line chart with weekly data | High |
| 4.4 AI Quality chart | Bar chart comparing AI vs non-AI | High |
| 4.5 Cycle Time chart | Line chart trend | High |
| 4.6 Team breakdown table | Member metrics | High |
| 4.7 Date filter | Changes data range | Medium |
| 4.8 HTMX lazy loading | Charts load asynchronously | High |

**UI Audit Points:**
- Chart rendering and sizing
- Card styling consistency
- Table styling and responsiveness
- Filter dropdown styling
- Loading spinners during HTMX loads

---

### Section 5: Team Dashboard

**Scope:** `/app/dashboard/team/`

| Test | Expected Behavior | Priority |
|------|------------------|----------|
| 5.1 Dashboard loads | All chart containers render | High |
| 5.2 Cycle time chart | Shows team trend | High |
| 5.3 Leaderboard table | AI Detective rankings | High |
| 5.4 Date filter | Changes data range | Medium |
| 5.5 Permission check | Non-admin can access | High |

**UI Audit Points:**
- Same as CTO dashboard
- Verify admin-only elements hidden

---

### Section 6: Team Settings

**Scope:** `/app/team/`

| Test | Expected Behavior | Priority |
|------|------------------|----------|
| 6.1 Team details | View/edit team name, slug | High |
| 6.2 Team members | List members, roles | High |
| 6.3 Invite member | Send invitation email | Medium |
| 6.4 Remove member | Remove from team | Medium |
| 6.5 Change role | Promote/demote member | Medium |

**UI Audit Points:**
- Form styling
- Member list table
- Action buttons (invite, remove)
- Confirmation modals

---

### Section 7: Data Sync Verification

**Scope:** Background jobs and data integrity

| Test | Expected Behavior | Priority |
|------|------------------|----------|
| 7.1 GitHub webhook | PR events create/update records | High |
| 7.2 GitHub sync job | Incremental sync works | High |
| 7.3 Jira sync job | Issues synced correctly | High |
| 7.4 Weekly metrics | Aggregation calculates | Medium |
| 7.5 Survey flow | PR merge triggers survey | High |
| 7.6 Reveal mechanism | Both responses trigger reveal | High |
| 7.7 Leaderboard posting | Weekly Slack post works | Medium |

**Testing Approach:**
- Use seed data to verify display
- Check Celery beat schedule
- Review task logs in admin

---

### Section 8: Landing Page & Marketing

**Scope:** `/` public pages

| Test | Expected Behavior | Priority |
|------|------------------|----------|
| 8.1 Landing page | Hero, features, CTA visible | High |
| 8.2 Mobile responsive | Layout adapts | High |
| 8.3 CTA buttons | Link to signup | High |
| 8.4 Footer links | Terms, privacy | Low |

**UI Audit Points:**
- Hero section styling
- Feature grid layout
- CTA button prominence
- Mobile menu functionality

---

## Implementation Approach

### Phase 1: Automated Test Verification (1-2 hours)

1. Run full test suite: `make test ARGS='--keepdb'`
2. Verify all 1071 tests pass
3. Check test coverage for critical paths

### Phase 2: Manual UI Review (3-4 hours)

Use **frontend-design skill** for systematic review:

1. **Authentication flows** - Login, signup, logout
2. **Onboarding wizard** - All steps with real OAuth
3. **Dashboard views** - CTO and Team dashboards
4. **Integration pages** - Connect/configure flows
5. **Settings pages** - Team management

For each screen:
- Screenshot current state
- Note styling issues
- Verify HTMX interactions
- Test mobile responsiveness

### Phase 3: Data Flow Verification (2 hours)

1. Seed demo data: `python manage.py seed_demo_data --clear`
2. Navigate through all dashboards
3. Verify charts show correct data
4. Test date filters affect data

### Phase 4: Integration Testing (2-3 hours)

With real credentials (if available):
1. GitHub OAuth flow end-to-end
2. Jira OAuth flow end-to-end
3. Slack OAuth flow end-to-end
4. Verify webhook delivery
5. Test survey flow manually

### Phase 5: Fix & Document (ongoing)

- Create issues for bugs found
- Update documentation
- Apply UI fixes using frontend-design skill

---

## Success Criteria

- [ ] All 1071 tests pass
- [ ] Every URL in the audit list accessible
- [ ] Charts render correctly with seed data
- [ ] OAuth flows complete successfully
- [ ] Mobile responsive on all pages
- [ ] No console errors in browser
- [ ] Loading states visible during HTMX requests
- [ ] Error states display properly

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OAuth tokens expired | Medium | High | Re-authenticate during testing |
| Missing seed data | Low | Medium | Run seed_demo_data first |
| Chart rendering issues | Medium | Medium | Test with multiple browsers |
| HTMX race conditions | Low | Medium | Add loading indicators |
| Mobile layout broken | Medium | Medium | Test with device simulator |

---

## Resources Required

- Local dev environment running
- Demo data seeded
- Browser dev tools open
- OAuth credentials (GitHub, Jira, Slack)
- Mobile device or simulator

---

## Estimated Effort

| Phase | Effort | Description |
|-------|--------|-------------|
| 1. Test Verification | S | Run existing tests |
| 2. UI Review | L | Manual walkthrough all screens |
| 3. Data Verification | M | Check charts and data |
| 4. Integration Testing | L | Real OAuth flows |
| 5. Fixes | Variable | Depends on issues found |

**Total: 8-12 hours for thorough review**
