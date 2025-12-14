# GitHub-Based Survey System Implementation Plan

**Last Updated:** 2024-12-13

## Executive Summary

Replace the Slack-dependent survey system with a GitHub-based alternative that posts survey invitations as PR comments with links to authenticated web forms. This eliminates Slack as a blocker for the core AI attribution feature while providing stronger identity verification through GitHub OAuth.

### Key Benefits
- **No Slack dependency** for core AI metrics collection
- **Reliable identity verification** via GitHub OAuth
- **Authorization enforcement** - only PR author/reviewers can respond
- **Higher engagement** - surveys appear where the work happens
- **Simpler user matching** - no email-based matching required

---

## Current State Analysis

### How Surveys Work Today (Slack-Based)

```
PR MERGED (GitHub webhook)
    |
    v
send_pr_surveys_task (Celery)
    |
    +-- Check: SlackIntegration exists?
    |       |
    |       NO --> return {"skipped": "No Slack integration"}  <-- PROBLEM!
    |       |
    |       YES --> continue
    |
    v
Create PRSurvey record
    |
    v
Send Slack DMs:
    - Author: "Was this PR AI-assisted?" [Yes] [No]
    - Reviewers: "Rate quality" + "Guess AI usage"
    |
    v
Collect responses via /webhooks/slack/interactions/
```

### Current Files Involved

| File | Purpose |
|------|---------|
| `apps/integrations/tasks.py` | `send_pr_surveys_task` - triggers surveys on merge |
| `apps/integrations/services/slack_surveys.py` | Builds Slack Block Kit messages |
| `apps/integrations/webhooks/slack_interactions.py` | Handles button responses |
| `apps/metrics/services/survey_service.py` | Business logic (create, record responses) |
| `apps/metrics/models.py` | `PRSurvey`, `PRSurveyReview` models |

### The Problem

- Slack integration is marked "Optional" in onboarding
- `send_pr_surveys_task` silently skips if no Slack
- Teams without Slack get **zero AI attribution data**
- Core product value proposition cannot be delivered

---

## Proposed Future State

### GitHub Comment + Web Survey Flow

```
PR MERGED (GitHub webhook)
    |
    v
post_survey_comment_task (Celery)
    |
    v
Create PRSurvey record + generate secure tokens
    |
    v
POST GitHub comment to merged PR:
    "📊 AI Impact Survey
     @author - Did you use AI assistance?
     → [Complete Survey](https://app/survey/{token})

     @reviewer1 @reviewer2 - Rate this PR:
     → [Complete Survey](https://app/survey/{token})"
    |
    v
User clicks link
    |
    v
Web Survey Flow:
    1. If not logged in → GitHub OAuth redirect
    2. Verify user is author OR reviewer of this PR
    3. Show appropriate survey form
    4. Record response
    5. (Optional) Update GitHub comment to show completion
```

### New Components Needed

| Component | Description |
|-----------|-------------|
| `SurveyToken` model | Secure, time-limited tokens for survey URLs |
| `github_comments.py` service | Post/update PR comments via PyGithub |
| `survey_views.py` | Web views for survey forms |
| `survey_urls.py` | URL patterns for surveys |
| Survey templates | HTMX-based form templates |
| `post_survey_comment_task` | Celery task to post comments |

---

## Implementation Phases

### Phase 1: Foundation - Survey Token & URL System (M)

Create secure token infrastructure for survey URLs.

#### 1.1 Add SurveyToken Model
- Add `token` field to `PRSurvey` model (or create separate `SurveyToken`)
- Generate cryptographically secure tokens (32 bytes, URL-safe base64)
- Add `expires_at` field (7 days from creation)
- Index for fast lookups

#### 1.2 Token Generation Service
- Create `apps/metrics/services/survey_tokens.py`
- `generate_survey_token(survey_id, role)` - generates signed token
- `validate_survey_token(token)` - validates and returns survey info
- Use Django's signing framework or HMAC

#### 1.3 URL Structure
```python
# Survey URLs (outside team context - public links)
urlpatterns = [
    path("survey/<str:token>/", survey_landing, name="survey_landing"),
    path("survey/<str:token>/author/", author_survey_form, name="author_survey"),
    path("survey/<str:token>/reviewer/", reviewer_survey_form, name="reviewer_survey"),
    path("survey/<str:token>/complete/", survey_complete, name="survey_complete"),
]
```

**Acceptance Criteria:**
- [ ] Tokens are cryptographically secure (32+ bytes)
- [ ] Tokens expire after 7 days
- [ ] Tokens encode survey ID and role
- [ ] Tokens are single-use or limited-use
- [ ] Invalid/expired tokens show clear error

---

### Phase 2: Web Survey Views & Templates (M)

Create the web-based survey forms.

#### 2.1 Survey Landing View
- `survey_landing(request, token)`
- Validate token
- Check if survey already completed
- Determine role (author/reviewer) from token
- Require GitHub OAuth login if not authenticated
- Verify user matches author/reviewer

#### 2.2 Author Survey Form
```
📊 AI Impact Survey

Your PR was merged:
"[PR Title]" in owner/repo

Did you use AI assistance (Copilot, Cursor, ChatGPT, etc.)?

[Yes, AI helped] [No, all manual]

[Submit]
```

#### 2.3 Reviewer Survey Form
```
📊 AI Impact Survey

You reviewed:
"[PR Title]" by @author

How would you rate the code quality?
○ Could be better  ○ OK  ○ Super

Was this PR AI-assisted?
○ Yes, I think so  ○ No, I don't think so

[Submit]
```

#### 2.4 Completion View
- Show thank you message
- If author responded and reviewer responded, show reveal
- Link back to PR

**Acceptance Criteria:**
- [ ] Forms work with HTMX (no full page reload)
- [ ] Mobile-responsive design
- [ ] Clear error messages for invalid/expired tokens
- [ ] Shows "already completed" if revisiting
- [ ] Integrates with existing survey_service.py

---

### Phase 3: Authorization & Identity Verification (S)

Ensure only authorized users can complete surveys.

#### 3.1 GitHub OAuth for Survey Access
- Survey views require authentication
- On unauthenticated access: redirect to GitHub OAuth
- After OAuth: redirect back to survey URL
- Store GitHub user ID in session/user model

#### 3.2 Authorization Checks
```python
def verify_survey_access(user, survey, role):
    """Verify user can access this survey with given role."""
    member = TeamMember.objects.filter(
        team=survey.team,
        github_id=user.github_id  # or social auth lookup
    ).first()

    if not member:
        raise PermissionDenied("You are not a member of this team")

    if role == "author":
        if member != survey.pull_request.author:
            raise PermissionDenied("You are not the author of this PR")
    elif role == "reviewer":
        reviewer_ids = survey.pull_request.reviews.values_list('reviewer_id', flat=True)
        if member.id not in reviewer_ids:
            raise PermissionDenied("You did not review this PR")

    return member
```

#### 3.3 Abuse Prevention
- Rate limit survey submissions (1 per token)
- Mark tokens as used after submission
- Log all access attempts

**Acceptance Criteria:**
- [ ] Unauthenticated users redirected to GitHub OAuth
- [ ] Only PR author can complete author survey
- [ ] Only PR reviewers can complete reviewer survey
- [ ] Clear error messages for unauthorized access
- [ ] Tokens become invalid after use

---

### Phase 4: GitHub Comment Service (M)

Post survey invitations as PR comments.

#### 4.1 Comment Service
Create `apps/integrations/services/github_comments.py`:

```python
def post_survey_comment(pr: PullRequest, survey: PRSurvey) -> int:
    """Post survey invitation comment to merged PR.

    Returns: GitHub comment ID
    """
    # Get access token
    integration = GitHubIntegration.objects.get(team=pr.team)
    access_token = decrypt(integration.credential.access_token)

    # Build @mentions
    author_mention = f"@{pr.author.github_username}"
    reviewers = pr.reviews.exclude(reviewer=pr.author).values_list(
        'reviewer__github_username', flat=True
    ).distinct()
    reviewer_mentions = " ".join(f"@{u}" for u in reviewers if u)

    # Generate URLs
    author_url = generate_survey_url(survey, "author")
    reviewer_url = generate_survey_url(survey, "reviewer")

    # Build comment
    comment = f"""📊 **AI Impact Survey**

{author_mention} - Did you use AI assistance for this PR?
→ [Complete Author Survey]({author_url})

{reviewer_mentions} - Rate this PR and guess AI usage:
→ [Complete Reviewer Survey]({reviewer_url})

_Responses are anonymous to teammates. Data used for team-level insights only._
"""

    # Post via PyGithub
    github = Github(access_token)
    repo = github.get_repo(pr.github_repo)
    issue = repo.get_issue(pr.github_pr_id)  # PRs are issues in GitHub API
    comment = issue.create_comment(comment)

    return comment.id
```

#### 4.2 Update Comment on Completion (Optional)
```python
def update_survey_comment_status(pr: PullRequest, comment_id: int):
    """Update comment to show completion status."""
    # Add checkmarks for completed responses
    # "✅ Author responded | ⏳ 1/2 reviewers"
```

**Acceptance Criteria:**
- [ ] Comments posted successfully via PyGithub
- [ ] @mentions work (trigger GitHub notifications)
- [ ] Links are correct and functional
- [ ] Handles repos with no reviewers gracefully
- [ ] Error handling for API failures

---

### Phase 5: Celery Task & Trigger Integration (S)

Wire up the new flow to the existing webhook system.

#### 5.1 New Celery Task
```python
@shared_task
def post_survey_comment_task(pull_request_id: int) -> dict:
    """Post survey comment to merged PR.

    Triggered when:
    - PR is merged AND
    - Team has GitHub integration with valid token

    Unlike Slack surveys, this doesn't require Slack integration.
    """
    pr = PullRequest.objects.get(id=pull_request_id)

    # Check if PR is merged
    if pr.state != "merged":
        return {"skipped": True, "reason": "PR not merged"}

    # Check if survey already exists
    if hasattr(pr, 'survey'):
        return {"skipped": True, "reason": "Survey already exists"}

    # Get GitHub integration
    try:
        integration = GitHubIntegration.objects.get(team=pr.team)
    except GitHubIntegration.DoesNotExist:
        return {"skipped": True, "reason": "No GitHub integration"}

    # Create survey
    survey = create_pr_survey(pr)

    # Post comment
    try:
        comment_id = post_survey_comment(pr, survey)
        survey.github_comment_id = comment_id
        survey.save()
        return {"success": True, "survey_id": survey.id, "comment_id": comment_id}
    except Exception as e:
        logger.error(f"Failed to post survey comment: {e}")
        return {"success": False, "error": str(e)}
```

#### 5.2 Trigger from GitHub Webhook
Modify existing webhook handler or add to sync process:
- When PR is synced with `state=merged`
- Trigger `post_survey_comment_task.delay(pr.id)`

#### 5.3 Coexistence with Slack
- GitHub comments become the **primary** survey channel
- Slack DMs become **optional secondary** channel
- If team has Slack AND surveys_enabled: send both
- This provides redundancy and choice

**Acceptance Criteria:**
- [ ] Task triggers on PR merge
- [ ] Doesn't duplicate comments on re-sync
- [ ] Works without Slack integration
- [ ] Idempotent (safe to retry)
- [ ] Proper error handling and logging

---

### Phase 6: Model Updates (S)

Minor model changes to support GitHub comments.

#### 6.1 PRSurvey Model Additions
```python
class PRSurvey(BaseTeamModel):
    # ... existing fields ...

    # New fields for GitHub comment tracking
    github_comment_id = models.BigIntegerField(
        null=True, blank=True,
        help_text="GitHub comment ID for survey invitation"
    )

    # Token for secure URLs
    token = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text="Secure token for survey URL"
    )
    token_expires_at = models.DateTimeField(
        help_text="When the survey token expires"
    )

    # Track completion status
    author_survey_sent_at = models.DateTimeField(null=True, blank=True)
    reviewers_survey_sent_at = models.DateTimeField(null=True, blank=True)
```

#### 6.2 Migration
- Add new fields with null defaults
- Generate tokens for existing surveys (backfill)
- Add index on token field

**Acceptance Criteria:**
- [ ] Migration runs without data loss
- [ ] Existing surveys work with new code
- [ ] Tokens indexed for fast lookup

---

### Phase 7: Testing (M)

Comprehensive test coverage.

#### 7.1 Unit Tests
- Token generation/validation
- Authorization checks
- Survey service functions

#### 7.2 Integration Tests
- Full flow: merge → comment → click → auth → submit
- GitHub API mocking
- OAuth flow

#### 7.3 Edge Cases
- User clicks link but not logged in
- User clicks link but not authorized
- Token expired
- Survey already completed
- PR has no reviewers
- Author is also reviewer (self-merge)

**Acceptance Criteria:**
- [ ] >80% code coverage on new code
- [ ] All edge cases tested
- [ ] GitHub API properly mocked

---

### Phase 8: Documentation & Cleanup (S)

#### 8.1 Update PRD
- Update `prd/SLACK-BOT.md` to mention GitHub comments as primary
- Update `prd/ONBOARDING.md` to reflect Slack being optional for surveys

#### 8.2 Feature Flag (Optional)
- Add feature flag to enable/disable GitHub comments
- Allows gradual rollout

#### 8.3 Deprecation Path for Slack-Only Surveys
- Mark Slack DM surveys as "legacy/optional"
- Keep for teams that prefer in-Slack experience

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub API rate limits | Medium | Medium | Cache tokens, batch requests |
| User ignores PR comment | Medium | Medium | Email notification fallback (future) |
| OAuth flow friction | Low | Medium | Clear UX, remember auth |
| Token security issues | Low | High | Use Django signing, short expiry |
| Comment spam perception | Low | Low | Single comment per PR, clean formatting |

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Survey response rate | >40% | Responses / Merged PRs |
| Time to respond | <24h median | Created → Responded timestamp |
| Auth success rate | >95% | Successful auth / Auth attempts |
| Error rate | <1% | Failed posts / Total posts |

---

## Required Resources

### Development Effort

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: Tokens | M (2-3 days) | None |
| Phase 2: Views | M (2-3 days) | Phase 1 |
| Phase 3: Auth | S (1 day) | Phase 2 |
| Phase 4: Comments | M (2 days) | Phase 1 |
| Phase 5: Tasks | S (1 day) | Phases 1, 4 |
| Phase 6: Models | S (0.5 days) | None |
| Phase 7: Testing | M (2 days) | All |
| Phase 8: Docs | S (0.5 days) | All |

**Total: ~10-12 days of focused development**

### Technical Dependencies

- PyGithub (already installed)
- Django signing framework (built-in)
- Existing OAuth infrastructure
- HTMX for forms (already in use)

---

## Appendix: Alternative Approaches Considered

### Option A: GitHub Check Runs
- Use Checks API to show survey status
- Rejected: Not interactive, poor UX

### Option B: GitHub Discussions
- Create discussion for each PR
- Rejected: Requires separate repo config

### Option C: Email-based Surveys
- Send email with survey link
- Considered for future: Good secondary channel

### Option D: Keep Slack-only, Make Required
- Remove "skip" option in onboarding
- Rejected: Too restrictive, many teams don't use Slack
