# Simplified Onboarding - Context

> Last Updated: 2025-12-11

## Key Files

### Files to Modify

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/teams/forms.py` | Signup form with team_name field | Remove `team_name` field, update `save()` |
| `apps/teams/signals.py` | Auto-creates team on signup | Remove auto-team creation |
| `apps/teams/helpers.py` | `create_default_team_for_user()` | Keep but don't call from signup |
| `apps/web/views.py` | Post-login routing | Redirect teamless users to onboarding |
| `templates/account/signup.html` | Signup template | Remove team_name field |
| `apps/integrations/views.py` | GitHub OAuth handling | Reuse for onboarding flow |

### Files to Create

| File | Purpose |
|------|---------|
| `apps/onboarding/__init__.py` | New app init |
| `apps/onboarding/apps.py` | App config |
| `apps/onboarding/views.py` | Onboarding wizard views |
| `apps/onboarding/urls.py` | URL patterns |
| `apps/onboarding/models.py` | OnboardingProgress model (optional) |
| `templates/onboarding/base.html` | Wizard base template |
| `templates/onboarding/start.html` | Step 1: Connect GitHub |
| `templates/onboarding/select_org.html` | Step 2: Select organization |
| `templates/onboarding/select_repos.html` | Step 3: Select repositories |
| `templates/onboarding/connect_jira.html` | Step 4: Connect Jira (optional) |
| `templates/onboarding/connect_slack.html` | Step 5: Connect Slack (optional) |
| `templates/onboarding/complete.html` | Step 6: Sync status |

### Reference Files

| File | Why Reference |
|------|---------------|
| `apps/integrations/services/github_oauth.py` | GitHub OAuth flow implementation |
| `apps/integrations/services/member_sync.py` | Team member sync from GitHub |
| `apps/teams/decorators.py` | `@login_and_team_required` pattern |
| `prd/ONBOARDING.md` | Updated onboarding specification |

---

## Key Decisions

### 1. Team Creation Location

**Decision:** Create team in onboarding GitHub callback, not existing integration views

**Rationale:**
- Onboarding flow is for users without teams
- Existing integration views assume team already exists
- Cleaner separation of concerns

### 2. Onboarding State Storage

**Decision:** Use session storage for onboarding progress

**Rationale:**
- Simple implementation
- No database model needed initially
- Can upgrade to database model later if needed

**Alternative considered:** Database model for `OnboardingProgress`
- Pro: Survives session expiry
- Con: More complexity for MVP

### 3. Handling Existing Integration Views

**Decision:** Keep existing GitHub integration views unchanged

**Rationale:**
- Existing views work for adding GitHub to existing teams
- Used for reconnecting or changing GitHub org
- Don't break existing functionality

### 4. Skip Buttons for Optional Steps

**Decision:** Allow skipping Jira and Slack steps

**Rationale:**
- Not all users have Jira/Slack
- Can connect later from settings
- Faster onboarding for MVP

---

## Dependencies

### Internal Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| GitHub OAuth service | Complete | `apps/integrations/services/github_oauth.py` |
| Member sync service | Complete | `apps/integrations/services/member_sync.py` |
| Token encryption | Complete | `apps/integrations/services/encryption.py` |
| Team model | Complete | `apps/teams/models.py` |

### External Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| GitHub OAuth App | Required | Must be configured in env |
| Jira OAuth | Optional | For Jira step |
| Slack OAuth | Optional | For Slack step |

---

## URL Structure

### New Onboarding URLs

```
/onboarding/                          → Start (Connect GitHub CTA)
/onboarding/github/                   → Initiates GitHub OAuth
/onboarding/github/callback/          → GitHub OAuth callback
/onboarding/org/                      → Select organization (if multiple)
/onboarding/repos/                    → Select repositories
/onboarding/jira/                     → Connect Jira (optional)
/onboarding/jira/callback/            → Jira OAuth callback
/onboarding/slack/                    → Connect Slack (optional)
/onboarding/slack/callback/           → Slack OAuth callback
/onboarding/complete/                 → Sync status & completion
```

### Existing Integration URLs (unchanged)

```
/a/<team_slug>/integrations/github/connect/    → Connect GitHub to existing team
/a/<team_slug>/integrations/github/callback/   → GitHub callback for existing team
```

---

## Data Flow

### New User Flow (After Implementation)

```
1. User visits /accounts/signup/
2. Fills form (email, password, terms) - NO team_name
3. Account created, user has no team
4. Redirected to /onboarding/
5. Clicks "Connect GitHub"
6. Redirected to GitHub OAuth
7. Authorizes app
8. Callback to /onboarding/github/callback/
9. If single org: auto-select, create team, redirect to /onboarding/repos/
10. If multiple orgs: show org selection at /onboarding/org/
11. User selects org
12. Team created with org name
13. GitHubIntegration created
14. Members synced from GitHub
15. Redirect to /onboarding/repos/
16. User selects repositories
17. Webhooks created for selected repos
18. Redirect to /onboarding/jira/ (optional)
19. User connects or skips
20. Redirect to /onboarding/slack/ (optional)
21. User connects or skips
22. Redirect to /onboarding/complete/
23. Shows sync status
24. User clicks "View Dashboard"
25. Redirected to /a/<team_slug>/
```

### Invitation Flow (Unchanged)

```
1. User receives invitation email
2. Clicks link to /accounts/signup/?invitation_id=xxx
3. Signs up with invited email
4. Automatically joins existing team
5. Redirected to team dashboard
```

---

## Testing Strategy

### Unit Tests

- `test_signup_without_team_name` - User can sign up without team
- `test_signup_creates_no_team` - Team not auto-created
- `test_invitation_still_works` - Invitations join existing teams
- `test_onboarding_redirect` - Teamless users go to onboarding

### Integration Tests

- `test_full_onboarding_flow` - Complete wizard flow
- `test_github_oauth_creates_team` - Team created from org
- `test_skip_optional_steps` - Can skip Jira/Slack
- `test_resume_onboarding` - Can resume abandoned wizard

### Manual Testing Checklist

- [ ] New user signup (no team created)
- [ ] Redirect to onboarding
- [ ] GitHub OAuth flow
- [ ] Organization selection (multiple orgs)
- [ ] Team creation with org name
- [ ] Repository selection
- [ ] Skip Jira step
- [ ] Skip Slack step
- [ ] Complete onboarding
- [ ] Arrive at dashboard
- [ ] Invitation flow still works

---

## Rollback Plan

If issues discovered:

1. **Revert form changes** - Re-add `team_name` field
2. **Revert signal changes** - Re-enable auto team creation
3. **Revert routing changes** - Remove onboarding redirect
4. **Keep onboarding app** - Can be used as optional path

Rollback is safe because:
- No database migrations (no schema changes)
- Existing users unaffected
- Only new signups use new flow
