# Simplified Onboarding Plan

> Last Updated: 2025-12-11

## Executive Summary

Simplify the user onboarding flow by removing the team creation step from signup and instead creating teams automatically when users connect their GitHub organization. This aligns with the "GitHub-first" principle where the GitHub org becomes the team.

### Key Changes

1. **Remove `team_name` field from signup form** - Users sign up with just email/password/terms
2. **Don't auto-create team on signup** - Users exist without a team initially
3. **Redirect to onboarding flow** - After signup, guide users to connect GitHub
4. **GitHub OAuth creates the team** - Team is created from the selected GitHub organization

### Why This Matters

- **Faster signup** - One less field to fill
- **Better data quality** - Team names match real GitHub orgs
- **Natural flow** - Connect GitHub first, everything else follows
- **Reduced confusion** - No more "My Team" placeholder names

---

## Current State Analysis

### Current Signup Flow

1. User fills signup form with:
   - Email
   - Password
   - **Team Name (Optional)** ← Problem: Often skipped, creates "john" teams
   - Terms agreement

2. `TeamSignupForm.save()` calls `create_default_team_for_user()`:
   - If no team_name provided, uses email prefix (e.g., "john" from john@example.com)
   - Creates team immediately

3. Post-signup redirect:
   - If user has team → `/a/<team_slug>/` (team dashboard)
   - If no team → `/teams/` (manage teams page)

4. User manually navigates to integrations to connect GitHub

### Current Files Involved

| File | Purpose |
|------|---------|
| `apps/teams/forms.py` | `TeamSignupForm` with `team_name` field |
| `apps/teams/signals.py` | `add_user_to_team` signal creates default team |
| `apps/teams/helpers.py` | `create_default_team_for_user()` function |
| `apps/web/views.py` | `home()` view handles post-login routing |
| `templates/account/signup.html` | Signup template with team_name field |

### Problems with Current Flow

1. **Poor team names** - "john", "jane", random email prefixes
2. **Disconnected from GitHub** - Team exists before GitHub is connected
3. **Extra step** - User must manually find and connect GitHub
4. **Confusion** - Team created but empty until GitHub connected

---

## Proposed Future State

### New Signup Flow

1. **Signup** (simplified):
   - Email
   - Password
   - Terms agreement
   - **No team_name field**

2. **Post-signup routing**:
   - User has no team → Redirect to `/onboarding/`
   - User has team (via invitation) → Redirect to team dashboard

3. **Onboarding wizard** (`/onboarding/`):
   - Step 1: Connect GitHub
   - Step 2: Select organization → **Team created here**
   - Step 3: Select repositories
   - Step 4: Connect Jira (optional)
   - Step 5: Connect Slack (optional)
   - Step 6: Initial sync status

4. **Team creation happens in GitHub OAuth callback**:
   - User selects org
   - Team created with org name as team name
   - User added as admin
   - Members synced from GitHub

### New Files to Create

| File | Purpose |
|------|---------|
| `apps/onboarding/` | New Django app for onboarding wizard |
| `apps/onboarding/views.py` | Wizard step views |
| `apps/onboarding/urls.py` | URL patterns for `/onboarding/` |
| `templates/onboarding/` | Templates for each wizard step |

### Files to Modify

| File | Changes |
|------|---------|
| `apps/teams/forms.py` | Remove `team_name` field from `TeamSignupForm` |
| `apps/teams/signals.py` | Don't auto-create team in `add_user_to_team` |
| `apps/web/views.py` | Redirect teamless users to `/onboarding/` |
| `templates/account/signup.html` | Remove team_name field rendering |
| `apps/integrations/views.py` | Create team when org is selected |

---

## Implementation Phases

### Phase 1: Remove Team Creation from Signup (Backend)

**Goal:** Users can sign up without creating a team

**Effort:** Medium

#### Tasks

1.1. Modify `TeamSignupForm` in `apps/teams/forms.py`:
   - Remove `team_name` field
   - Remove `_clean_team_name()` method
   - Update `save()` to not create team

1.2. Modify `add_user_to_team` signal in `apps/teams/signals.py`:
   - Don't call `create_default_team_for_user()` for new signups
   - Keep invitation handling logic

1.3. Update signup template `templates/account/signup.html`:
   - Remove `{% render_field form.team_name %}` line

1.4. Write tests for new signup flow:
   - Test user can sign up without team
   - Test user with invitation still joins team
   - Test existing team creation paths still work

---

### Phase 2: Create Onboarding App

**Goal:** New Django app to handle onboarding wizard

**Effort:** Large

#### Tasks

2.1. Create new Django app:
   ```bash
   make uv run 'pegasus startapp onboarding'
   ```

2.2. Create onboarding models (if needed):
   - `OnboardingProgress` model to track user's progress through wizard
   - Fields: `user`, `current_step`, `completed_at`, `github_connected`, etc.

2.3. Create onboarding views:
   - `onboarding_start()` - Entry point, shows "Connect GitHub" step
   - `onboarding_github_callback()` - Handles GitHub OAuth, creates team
   - `onboarding_select_repos()` - Repository selection
   - `onboarding_connect_jira()` - Optional Jira connection
   - `onboarding_connect_slack()` - Optional Slack connection
   - `onboarding_complete()` - Shows sync status, redirects to dashboard

2.4. Create URL patterns:
   ```python
   urlpatterns = [
       path("", views.onboarding_start, name="start"),
       path("github/callback/", views.onboarding_github_callback, name="github_callback"),
       path("repos/", views.onboarding_select_repos, name="select_repos"),
       path("jira/", views.onboarding_connect_jira, name="connect_jira"),
       path("slack/", views.onboarding_connect_slack, name="connect_slack"),
       path("complete/", views.onboarding_complete, name="complete"),
   ]
   ```

2.5. Create templates:
   - `templates/onboarding/base.html` - Wizard layout with progress indicator
   - `templates/onboarding/start.html` - "Connect GitHub" CTA
   - `templates/onboarding/select_org.html` - Organization selection
   - `templates/onboarding/select_repos.html` - Repository selection
   - `templates/onboarding/connect_jira.html` - Jira connection (with skip)
   - `templates/onboarding/connect_slack.html` - Slack connection (with skip)
   - `templates/onboarding/complete.html` - Success page with sync status

---

### Phase 3: GitHub OAuth Creates Team

**Goal:** Team is created when user selects GitHub organization

**Effort:** Medium

#### Tasks

3.1. Modify GitHub OAuth callback in onboarding:
   - After user selects org, create Team with org name
   - Add user as admin of new team
   - Create GitHubIntegration linked to team
   - Trigger member sync

3.2. Handle edge cases:
   - User already has a team (should not happen in onboarding flow)
   - GitHub org name conflicts with existing team slug
   - User cancels OAuth flow

3.3. Update existing GitHub integration views:
   - Keep existing flow for adding GitHub to existing team
   - Ensure both paths work correctly

---

### Phase 4: Update Post-Login Routing

**Goal:** Route users appropriately based on onboarding status

**Effort:** Small

#### Tasks

4.1. Modify `home()` view in `apps/web/views.py`:
   ```python
   def home(request):
       if request.user.is_authenticated:
           team = request.default_team
           if team:
               return HttpResponseRedirect(reverse("web_team:home", args=[team.slug]))
           else:
               # No team = needs onboarding
               return HttpResponseRedirect(reverse("onboarding:start"))
       else:
           return render(request, "web/landing_page.html")
   ```

4.2. Add middleware or decorator to protect app routes:
   - Users without teams can only access onboarding
   - Redirect to onboarding if trying to access team routes

---

### Phase 5: Polish and Edge Cases

**Goal:** Handle all edge cases and polish UX

**Effort:** Medium

#### Tasks

5.1. Handle invitation flow:
   - Users with invitations skip onboarding
   - Join existing team instead

5.2. Add "Back" navigation in wizard:
   - Allow users to go back to previous steps
   - Preserve entered data

5.3. Add progress persistence:
   - If user abandons wizard, resume where they left off
   - Store progress in session or database

5.4. Error handling:
   - GitHub OAuth failure → Show error, allow retry
   - No organizations found → Show helpful message
   - API rate limits → Queue and show "processing" state

5.5. Skip functionality:
   - "Skip" buttons for Jira/Slack steps
   - Can connect later from settings

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Users confused by teamless state | Medium | Medium | Clear messaging, immediate redirect to onboarding |
| GitHub OAuth failure blocks signup | Low | High | Allow manual team creation as fallback |
| Existing users affected | Low | Medium | Only affects new signups, existing users unchanged |
| Invitation flow breaks | Medium | High | Thorough testing, keep invitation logic separate |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Signup completion rate | Unknown | +10% |
| Time to first dashboard view | ~5 min | <3 min |
| Teams with meaningful names | ~30% | >90% |
| GitHub connection rate | Unknown | >80% |

---

## Required Resources

### Development

- 1 developer
- Estimated effort: 3-5 days

### Dependencies

- GitHub OAuth already implemented
- Member sync service already exists
- No new external dependencies

### Testing

- Unit tests for new signup flow
- Integration tests for onboarding wizard
- Manual QA for full flow

---

## Technical Details

### Database Changes

No schema changes required. Existing models support this flow:
- `Team` - Will be created during onboarding
- `Membership` - Links user to team
- `GitHubIntegration` - Created when GitHub connected
- `IntegrationCredential` - Stores OAuth token

### API Endpoints

No new API endpoints required. All views are server-rendered Django templates.

### Session Management

Store onboarding state in session:
```python
request.session["onboarding"] = {
    "started_at": "2025-12-11T10:00:00Z",
    "github_token": "encrypted_token",  # Temporary until team created
    "selected_org": "acme-corp",
}
```

### Security Considerations

- OAuth tokens stored encrypted (existing `encrypt()` function)
- CSRF protection on all forms
- Rate limiting on OAuth endpoints
- Session expiry for abandoned onboarding
