# Skip Responded Reviewers - Context Document

**Last Updated:** 2025-12-13

## Key Files

### Primary Files to Modify

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `apps/integrations/tasks.py` | Celery tasks for surveys | 272-373: `send_pr_surveys_task` |
| `apps/integrations/tests/test_tasks.py` | Task tests | Add new test class |

### Reference Files (Read Only)

| File | Purpose | Relevant Info |
|------|---------|---------------|
| `apps/metrics/models.py` | Data models | 675-737: `PRSurveyReview` with `responded_at` |
| `apps/metrics/models.py` | Data models | 598-673: `PRSurvey` with `author_ai_assisted` |
| `apps/web/views.py` | GitHub survey handling | 235-276: `_handle_reviewer_submission` |
| `apps/integrations/webhooks/slack_interactions.py` | Slack survey handling | 111-165: `handle_reviewer_response` |

## Key Code Patterns

### Current Reviewer DM Loop (tasks.py:350-367)

```python
for reviewer in reviewers:
    if not reviewer.slack_user_id:
        logger.info(f"Skipping reviewer {reviewer.display_name} - no slack_user_id")
        continue

    try:
        # Create reviewer survey entry (side effect - record in DB)
        create_reviewer_survey(survey, reviewer)

        # Build and send reviewer survey blocks
        blocks = build_reviewer_survey_blocks(pr, survey, reviewer)
        send_dm(client, reviewer.slack_user_id, blocks, text="PR Review Survey")
        reviewers_sent += 1
        logger.info(f"Sent reviewer survey to {reviewer.display_name}")
    except Exception as e:
        # ... error handling
```

### Target Pattern (After Implementation)

```python
for reviewer in reviewers:
    if not reviewer.slack_user_id:
        logger.info(f"Skipping reviewer {reviewer.display_name} - no slack_user_id")
        continue

    # Check if reviewer already responded via GitHub
    if PRSurveyReview.objects.filter(
        survey=survey,
        reviewer=reviewer,
        responded_at__isnull=False
    ).exists():
        logger.info(f"Skipping reviewer {reviewer.display_name} - already responded via GitHub")
        reviewers_skipped += 1
        continue

    try:
        # ... existing code
```

### Author DM Check (tasks.py:325)

```python
# Current:
if pr.author and pr.author.slack_user_id:
    # Send DM

# Target:
if pr.author and pr.author.slack_user_id:
    # Check if author already responded
    if survey.author_ai_assisted is not None:
        logger.info(f"Skipping author {pr.author.display_name} - already responded via GitHub")
        author_skipped = True
    else:
        # Send DM
```

## Model Schema

### PRSurvey (One per PR)

```python
class PRSurvey(BaseTeamModel):
    pull_request = OneToOneField(PullRequest)  # Only ONE survey per PR
    author = ForeignKey(TeamMember)
    author_ai_assisted = BooleanField(null=True)  # None = not responded
    author_responded_at = DateTimeField(null=True)  # When author responded
    token = CharField(unique=True)  # For GitHub web survey URL
    token_expires_at = DateTimeField()
    github_comment_id = BigIntegerField(null=True)  # GitHub comment ID
```

### PRSurveyReview (One per Reviewer per Survey)

```python
class PRSurveyReview(BaseTeamModel):
    survey = ForeignKey(PRSurvey)
    reviewer = ForeignKey(TeamMember)
    quality_rating = IntegerField(choices=1-3, null=True)
    ai_guess = BooleanField(null=True)
    guess_correct = BooleanField(null=True)
    responded_at = DateTimeField(null=True)  # KEY FIELD - None = not responded

    class Meta:
        constraints = [UniqueConstraint(fields=["survey", "reviewer"])]
```

## Test Patterns

### Existing Test Pattern (test_tasks.py)

```python
class TestSendPrSurveysTask(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.pr = PullRequestFactory(team=self.team, state="merged")
        self.slack_integration = SlackIntegrationFactory(
            team=self.team,
            surveys_enabled=True
        )

    @patch("apps.integrations.tasks.get_slack_client")
    @patch("apps.integrations.tasks.send_dm")
    def test_sends_reviewer_dm(self, mock_send_dm, mock_client):
        # ... test setup and assertions
```

### New Test Cases Needed

1. `test_skip_reviewer_already_responded_via_github`
2. `test_skip_author_already_responded_via_github`
3. `test_sends_dm_when_reviewer_has_not_responded`
4. `test_task_returns_skipped_counts`
5. `test_logs_skip_reason_for_responded_reviewer`

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Check location | In `send_pr_surveys_task` before DM | Minimal change, single point of control |
| Check method | `.filter().exists()` | Efficient, doesn't load full object |
| Return value | Add `reviewers_skipped`, `author_skipped` | Observability without changing success criteria |
| Logging level | INFO | Normal operation, not error |

## Dependencies

- `PRSurveyReview` model with `responded_at` field (exists)
- `PRSurvey` model with `author_ai_assisted` field (exists)
- GitHub survey system implemented (completed in prior work)
- Factory: `PRSurveyReviewFactory` (exists in `apps/metrics/factories.py`)

## Edge Cases

1. **Race condition**: Both tasks run at same time
   - Mitigation: Check is idempotent, duplicate notification is acceptable edge case

2. **Survey created without PRSurveyReview**: GitHub comment posted but reviewer hasn't clicked link yet
   - Expected behavior: Slack DM should still be sent

3. **PRSurveyReview exists but `responded_at` is None**: Created by Slack task but not yet responded
   - Expected behavior: Should NOT skip (they haven't actually responded)

4. **Reviewer responded via Slack first**: Then GitHub comment is clicked
   - Web view already handles this (checks `responded_at` before saving)
