# GitHub Surveys - Context Document

**Last Updated:** 2024-12-13

## Key Files Reference

### Core Survey Logic (Existing - To Be Extended)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `apps/metrics/models.py` | Survey data models | `PRSurvey`, `PRSurveyReview` |
| `apps/metrics/services/survey_service.py` | Business logic | `create_pr_survey()`, `record_author_response()`, `record_reviewer_response()` |
| `apps/metrics/factories.py` | Test factories | `PRSurveyFactory`, `PRSurveyReviewFactory` |

### Current Slack Implementation (Reference Only)

| File | Purpose | Notes |
|------|---------|-------|
| `apps/integrations/services/slack_surveys.py` | Slack message templates | Block Kit builders - pattern for message content |
| `apps/integrations/webhooks/slack_interactions.py` | Response handler | Pattern for response handling |
| `apps/integrations/tasks.py:264-303` | Survey trigger task | `send_pr_surveys_task()` - to be replaced/extended |

### GitHub Integration (To Be Used)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `apps/integrations/models.py` | Integration credentials | `GitHubIntegration`, `IntegrationCredential` |
| `apps/integrations/services/github_webhooks.py` | Webhook utilities | Pattern for GitHub API calls |
| `apps/integrations/services/encryption.py` | Token encryption | `encrypt()`, `decrypt()` |
| `apps/web/webhooks.py` | GitHub webhook receiver | Trigger point for survey comments |

### Authentication (Existing)

| File | Purpose | Notes |
|------|---------|-------|
| `apps/users/models.py` | User model | `CustomUser` - may need GitHub ID field |
| `tformance/settings.py` | OAuth config | django-allauth settings for GitHub |
| `apps/web/decorators.py` | Auth decorators | `@login_and_team_required` pattern |

---

## Data Model Relationships

```
Team
 └── TeamMember (github_id, github_username)
      └── PullRequest (author)
           ├── PRReview (reviewer → TeamMember)
           └── PRSurvey (1:1)
                ├── author_ai_assisted
                ├── token (NEW)
                ├── github_comment_id (NEW)
                └── PRSurveyReview (1:many)
                     ├── reviewer
                     ├── quality_rating
                     └── ai_guess

GitHubIntegration
 └── IntegrationCredential (encrypted access_token)
```

---

## Key Decisions Made

### 1. URL Structure - Public vs Team-Scoped

**Decision:** Survey URLs are **public** (not team-scoped)

**Rationale:**
- Links shared via GitHub comments must work for anyone who clicks
- Auth happens when user visits the URL
- Team context derived from survey → PR → team relationship

```python
# Survey URLs go in apps/web/urls.py (not team_urlpatterns)
urlpatterns = [
    path("survey/<str:token>/", views.survey_landing, name="survey_landing"),
]
```

### 2. Token Strategy - Survey Model vs Separate Table

**Decision:** Add `token` field directly to `PRSurvey` model

**Rationale:**
- Simpler implementation
- 1:1 relationship with survey
- No need for separate table management
- Token encodes role (author/reviewer) in URL path, not token itself

### 3. Auth Strategy - Require Login vs Anonymous

**Decision:** **Require GitHub OAuth login**

**Rationale:**
- Verification that responder is actually the author/reviewer
- Prevents survey stuffing
- Aligns with product's GitHub-first approach
- Users already have GitHub accounts (they made the PR)

### 4. Coexistence with Slack

**Decision:** Keep both channels, GitHub becomes **primary**

**Rationale:**
- Some teams may prefer Slack experience
- GitHub comments work for all teams
- Redundancy increases response rates
- Easy to disable Slack channel if desired

### 5. Comment Update Strategy

**Decision:** Post once, **do not update** comment on response

**Rationale:**
- Simpler implementation
- Avoids revealing who responded/didn't
- Less API calls
- Can revisit if needed

---

## Technical Constraints

### GitHub API Limits

- **Rate limit:** 5000 requests/hour for authenticated requests
- **Comment limit:** No hard limit, but avoid spam
- **Webhook payload:** Max 25 MB

### Token Security Requirements

- Must be cryptographically random (32+ bytes)
- Must be URL-safe (base64url encoding)
- Must expire (7 days default)
- Should be single-use or limited-use
- Must not expose survey/user IDs directly

### OAuth Considerations

- User must have GitHub OAuth configured in django-allauth
- Callback URL must be registered with GitHub app
- User may have multiple GitHub accounts (edge case)

---

## URL Patterns

### New Survey URLs (Public)

```python
# apps/web/urls.py (or apps/surveys/urls.py if new app)
urlpatterns = [
    # Landing page - determines role and redirects
    path("survey/<str:token>/", survey_landing, name="survey_landing"),

    # Author survey form
    path("survey/<str:token>/author/", author_survey, name="author_survey"),

    # Reviewer survey form
    path("survey/<str:token>/reviewer/", reviewer_survey, name="reviewer_survey"),

    # Completion page
    path("survey/<str:token>/complete/", survey_complete, name="survey_complete"),

    # API endpoint for HTMX form submission
    path("survey/<str:token>/submit/", survey_submit, name="survey_submit"),
]
```

### OAuth Return URL

```python
# After GitHub OAuth, return to survey
# Use Django's ?next= parameter
LOGIN_REDIRECT_URL = "/"  # Default, but survey view handles redirect
```

---

## Template Structure

```
templates/
└── surveys/
    ├── base_survey.html       # Base template for survey pages
    ├── landing.html           # Determines role, shows login button
    ├── author_form.html       # Author survey form
    ├── reviewer_form.html     # Reviewer survey form
    ├── complete.html          # Thank you page
    ├── error.html             # Error states (expired, unauthorized)
    └── components/
        ├── quality_rating.html    # Radio button component
        └── ai_guess.html          # Yes/No button component
```

---

## Environment Variables

```bash
# Already configured
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx

# May need
SURVEY_TOKEN_SECRET=xxx  # For signing tokens (or use Django SECRET_KEY)
SURVEY_TOKEN_EXPIRY_DAYS=7
```

---

## Test Fixtures Needed

```python
# Minimal test setup
team = TeamFactory()
member_author = TeamMemberFactory(team=team, github_username="author", github_id="123")
member_reviewer = TeamMemberFactory(team=team, github_username="reviewer", github_id="456")

pr = PullRequestFactory(team=team, author=member_author, state="merged")
review = PRReviewFactory(team=team, pull_request=pr, reviewer=member_reviewer)

survey = PRSurveyFactory(team=team, pull_request=pr, author=member_author)
```

---

## Dependencies

### Python Packages (Already Installed)

- `PyGithub` - GitHub API client
- `django-allauth` - OAuth handling
- `cryptography` - Token encryption (if needed)

### No New Dependencies Required

All needed functionality can be built with existing packages.

---

## Migration Strategy

### For Existing Data

1. Add new fields with `null=True, blank=True`
2. Generate tokens for existing open surveys (optional)
3. Don't backfill `github_comment_id` - those comments were never posted

### Migration Example

```python
# Generated migration
class Migration(migrations.Migration):
    dependencies = [
        ('metrics', 'previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='prsurvey',
            name='token',
            field=models.CharField(max_length=64, null=True, blank=True, unique=True),
        ),
        migrations.AddField(
            model_name='prsurvey',
            name='token_expires_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='prsurvey',
            name='github_comment_id',
            field=models.BigIntegerField(null=True, blank=True),
        ),
    ]
```

---

## Error Handling Reference

| Error State | User Message | Action |
|-------------|--------------|--------|
| Token not found | "This survey link is invalid." | Show error page |
| Token expired | "This survey link has expired." | Show error page + contact info |
| Not logged in | "Please sign in with GitHub to continue." | Show login button |
| Not authorized (wrong user) | "You're not authorized to complete this survey." | Show error page |
| Already completed | "You've already completed this survey." | Show completion page |
| PR not found | "The pull request for this survey no longer exists." | Show error page |

---

## Related PRD Sections

- `prd/SLACK-BOT.md` - Original survey message templates
- `prd/ONBOARDING.md:158-171` - Slack optional step
- `prd/DASHBOARDS.md` - Where survey data is displayed
- `prd/DATA-MODEL.md` - Survey data model spec
