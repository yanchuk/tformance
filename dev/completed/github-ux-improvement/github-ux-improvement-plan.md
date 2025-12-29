# GitHub UX Improvement - Better Messaging for GitHub-Authenticated Users

Last Updated: 2025-12-29

## Executive Summary

Improve the UX for users who signed up via GitHub OAuth by showing context-aware messaging on the onboarding start page. Instead of a generic "Connect GitHub" button, users who already authenticated with GitHub should see "Grant Repository Access" with explanatory text about why additional permissions are needed.

## Problem Statement

Currently, users who sign up via GitHub OAuth (using django-allauth) see "Connect GitHub" on the onboarding page, which is confusing. They already authenticated with GitHub for login, so asking them to "connect" again creates cognitive dissonance.

**Root Cause:** Two separate OAuth flows exist:
1. **Login OAuth** (allauth): Grants `profile` and `email` scopes only
2. **Integration OAuth** (custom): Grants `read:org`, `repo`, `read:user`, `manage_billing:copilot` scopes

These tokens cannot be reused because GitHub OAuth tokens are scope-specific.

## Current State Analysis

### Relevant Files
- `templates/onboarding/start.html` - Onboarding start page with "Connect GitHub" button
- `apps/onboarding/views.py` - `onboarding_start` view (lines 42-54)
- `apps/allauth_settings.py` - Login OAuth scopes (lines 35-40)
- `apps/integrations/services/github_oauth.py` - Integration OAuth scopes (lines 17-25)

### Current Behavior
- All users see identical messaging regardless of signup method
- Button text: "Connect GitHub"
- Subtext: "We'll import your team from GitHub and start tracking engineering metrics."

## Proposed Future State

### Context-Aware Messaging

**For users who signed up via GitHub:**
- Heading: "Grant Repository Access"
- Subtext: "You signed in with GitHub. We need additional permissions to access your repositories and track engineering metrics."
- Button text: "Grant Access"

**For users who signed up via email:**
- Heading: "Connect Your GitHub Organization" (unchanged)
- Subtext: Same as current
- Button text: "Connect GitHub" (unchanged)

### Implementation Approach

1. Add `has_github_social` context variable to `onboarding_start` view
2. Update `start.html` template with conditional rendering
3. Ensure tests cover both scenarios

## Implementation Phases

### Phase 1: Backend Changes
Modify `onboarding_start` view to detect GitHub social account.

### Phase 2: Frontend Changes
Update template with conditional messaging using Django template tags.

### Phase 3: Testing
Add tests for both user types (GitHub signup vs email signup).

## Technical Design

### Backend Change (views.py)

```python
from allauth.socialaccount.models import SocialAccount

@login_required
def onboarding_start(request):
    """Start of onboarding wizard - prompts user to connect GitHub."""
    if request.user.teams.exists():
        return redirect("web:home")

    # Check if user signed up via GitHub
    has_github_social = SocialAccount.objects.filter(
        user=request.user,
        provider='github'
    ).exists()

    return render(
        request,
        "onboarding/start.html",
        {
            "page_title": _("Connect GitHub"),
            "step": 1,
            "has_github_social": has_github_social,
        },
    )
```

### Frontend Change (start.html)

```html
{% if has_github_social %}
  <h1>Grant Repository Access</h1>
  <p>You signed in with GitHub. We need additional permissions to access your repositories...</p>
  <button>Grant Access</button>
{% else %}
  <h1>Connect Your GitHub Organization</h1>
  <p>We'll import your team from GitHub...</p>
  <button>Connect GitHub</button>
{% endif %}
```

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| SocialAccount query performance | Low | Low | Query is indexed, single DB hit |
| Template complexity | Low | Low | Simple if/else conditional |
| Breaking existing tests | Medium | Medium | Run full test suite before merge |

## Success Metrics

1. All existing onboarding tests pass
2. New tests verify both messaging variants
3. No regression in onboarding completion rate

## Dependencies

- `allauth.socialaccount.models.SocialAccount` - Already installed
- No new packages required
