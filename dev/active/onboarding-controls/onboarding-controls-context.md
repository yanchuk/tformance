# Onboarding Controls Context

**Last Updated: 2025-12-23**

## Key Files

### Views
- `apps/onboarding/views.py` - Onboarding wizard views (start, select_org, repos, jira, slack, complete, skip_onboarding)
- `apps/onboarding/urls.py` - URL patterns for onboarding app

### Templates
- `templates/onboarding/base.html` - Base template with nav and step progress indicator
- `templates/onboarding/start.html` - GitHub connection page (Step 1)
- `templates/onboarding/select_org.html` - Organization selection
- `templates/onboarding/select_repos.html` - Repository selection
- `templates/onboarding/connect_jira.html` - Optional Jira connection
- `templates/onboarding/connect_slack.html` - Optional Slack connection
- `templates/onboarding/complete.html` - Setup complete page

### Tests
- `apps/onboarding/tests/test_views.py` - Unit tests for onboarding views (including skip_onboarding)
- `tests/e2e/onboarding.spec.ts` - E2E tests for onboarding flow

### Design System
- `assets/styles/app/tailwind/design-system.css` - CSS utility classes
- `assets/styles/site-tailwind.css` - Theme definitions (tformance, tformance-light)

## Key Decisions

### 1. Skip Behavior
**Decision**: Skip creates a team using email prefix and redirects to dashboard
**Rationale**: Users can explore the app without connecting GitHub, then connect later from Integrations

### 2. Logout Destination
**Decision**: Use Django allauth's `account_logout` URL
**Rationale**: Standard allauth logout flow handles session cleanup properly

### 3. Button Styling
**Decision**: Use `app-btn-ghost` for logout (subtle), text link for skip
**Rationale**: Primary action (Connect GitHub) should remain prominent; secondary actions should be subtle

### 4. Skip Flow Implementation
**Decision**: Create team with "{email_prefix}'s Team" naming
**Rationale**: Provides a meaningful default name while allowing users to rename later

## Dependencies

### Django URLs Referenced
- `account_logout` - Django allauth logout URL
- `web:home` - Main app entry point (`/app/`)
- `onboarding:start` - Onboarding start page
- `onboarding:skip` - Skip onboarding endpoint (new)

### CSS Classes Used
- `app-navbar` - Top navigation bar styling
- `app-btn-ghost` - Ghost button styling
- `app-btn-primary` - Primary button (existing GitHub connect button)
- `text-base-content/70` - Muted text color

### Font Awesome Icons
- `fa-brands fa-github` - GitHub logo (existing)
- `fa-solid fa-right-from-bracket` - Logout icon
- `fa-solid fa-shield-halved` - Privacy shield icon

## Implementation Summary

### Skip Flow
1. User on `/onboarding/` sees "Skip for now" link
2. Clicking skip calls `/onboarding/skip/`
3. View creates team using email prefix (e.g., "john's Team")
4. User becomes admin of the team
5. Redirected to dashboard with message: "Connect GitHub from Integrations to unlock all features"

### Logout Flow
1. Logout button visible in onboarding nav bar on all pages
2. Clicking logs user out via Django allauth
3. User redirected to home page

### Value Messaging Structure
Each onboarding step now shows:
- What data we access (with correct OAuth scope)
- Why we need it (value to CTO)
- Privacy assurances where appropriate

## Test Results

- **Unit Tests**: 9 passed (4 new for skip_onboarding)
- **E2E Tests**: 15 passed, 1 skipped
- **No regressions**

## Notes

### Users Without Teams
- `onboarding_start` view checks `request.user.teams.exists()`
- If no teams, shows onboarding start page
- If has teams, redirects to `web:home`

### Skip Creates Team
- Skip now creates a team automatically
- User can connect GitHub later from Integrations page
- Dashboard shows setup wizard for users without integrations
