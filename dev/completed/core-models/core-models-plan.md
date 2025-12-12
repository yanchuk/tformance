# Phase 1: Core Data Models Implementation Plan

**Last Updated:** 2025-12-10

## Executive Summary

Implement Django models for all engineering metrics data. This phase creates the foundation for GitHub, Jira, Slack integrations and dashboards. All models will be team-scoped using `BaseTeamModel` pattern.

### Core Value
> Store all metrics in our database with proper team isolation, enabling the full data pipeline for AI impact analytics.

### Key Deliverables
1. `apps/metrics/` Django app with all data models
2. TeamMember model for cross-integration user identity
3. GitHub models: PullRequest, PRReview, Commit
4. Jira models: JiraIssue
5. AI/Survey models: AIUsageDaily, PRSurvey, PRSurveyReview
6. Aggregation model: WeeklyMetrics
7. Comprehensive test coverage
8. Admin interface for debugging

---

## Current State Analysis

### What Exists
| Component | Status | Location |
|-----------|--------|----------|
| Team model | Complete | `apps/teams/models.py` |
| BaseTeamModel | Complete | `apps/teams/models.py` |
| TeamScopedManager | Complete | `apps/teams/models.py` |
| BaseModel (timestamps) | Complete | `apps/utils/models.py` |
| User model (auth) | Complete | `apps/users/models.py` |
| Example pattern | Complete | `apps/teams_example/models.py` |

### What's Missing
- `apps/metrics/` app for engineering data
- TeamMember model (integration user identities)
- All GitHub/Jira/AI metrics models
- Survey response models
- Weekly aggregation model

---

## Proposed Architecture

### App Structure
```
apps/metrics/
├── __init__.py
├── admin.py           # Admin for all models
├── apps.py
├── models.py          # All models in one file (can split later)
├── managers.py        # Custom managers if needed
├── migrations/
│   └── __init__.py
└── tests/
    ├── __init__.py
    ├── test_models.py
    └── test_managers.py
```

### Model Hierarchy
```
BaseTeamModel (from apps.teams)
├── TeamMember (integration identities)
├── PullRequest
│   ├── PRReview (ForeignKey to PR)
│   └── Commit (ForeignKey to PR)
├── JiraIssue
├── AIUsageDaily
├── PRSurvey (OneToOne with PR)
│   └── PRSurveyReview (ForeignKey to Survey)
└── WeeklyMetrics (aggregated data)
```

### Data Flow
```
GitHub API → PullRequest, PRReview, Commit
                    ↓
Jira API → JiraIssue → TeamMember (user matching)
                    ↓
Slack Bot → PRSurvey, PRSurveyReview
                    ↓
Celery Job → WeeklyMetrics (aggregation)
```

---

## Implementation Phases

### Phase 1.1: App Setup & TeamMember Model
**Effort: S**

Create the metrics app and implement TeamMember model which links integration identities (GitHub, Jira, Slack) to a team.

**Why first:** All other models reference TeamMember for user attribution.

### Phase 1.2: GitHub Models
**Effort: M**

Implement PullRequest, PRReview, and Commit models with calculated fields for cycle time and review time.

**Why second:** GitHub is the primary data source, and PRs trigger surveys.

### Phase 1.3: Jira Models
**Effort: S**

Implement JiraIssue model for project management metrics.

**Why third:** Simpler than GitHub, follows same pattern.

### Phase 1.4: AI Usage & Survey Models
**Effort: M**

Implement AIUsageDaily for Copilot metrics and PRSurvey/PRSurveyReview for the AI Detective game.

**Why fourth:** Depends on PullRequest model existing.

### Phase 1.5: Weekly Metrics & Aggregation
**Effort: M**

Implement WeeklyMetrics model for pre-computed dashboard data.

**Why fifth:** Aggregates data from all other models.

---

## Detailed Model Specifications

### TeamMember
```python
class TeamMember(BaseTeamModel):
    """
    Represents a team member with integration identities.
    Links GitHub/Jira/Slack users to a single team member.
    """
    email = models.EmailField(blank=True)
    display_name = models.CharField(max_length=255)

    # Integration identities
    github_username = models.CharField(max_length=100, blank=True)
    github_id = models.CharField(max_length=50, blank=True)
    jira_account_id = models.CharField(max_length=100, blank=True)
    slack_user_id = models.CharField(max_length=50, blank=True)

    # Role within the team
    ROLE_CHOICES = [
        ('developer', 'Developer'),
        ('lead', 'Lead'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='developer')

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'github_id'],
                condition=models.Q(github_id__gt=''),
                name='unique_team_github_id'
            ),
            models.UniqueConstraint(
                fields=['team', 'email'],
                condition=models.Q(email__gt=''),
                name='unique_team_email'
            ),
        ]
```

### PullRequest
```python
class PullRequest(BaseTeamModel):
    """GitHub Pull Request with calculated metrics."""

    STATE_CHOICES = [
        ('open', 'Open'),
        ('merged', 'Merged'),
        ('closed', 'Closed'),
    ]

    github_pr_id = models.BigIntegerField()
    github_repo = models.CharField(max_length=255)
    title = models.TextField(blank=True)
    author = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True, related_name='pull_requests')
    state = models.CharField(max_length=20, choices=STATE_CHOICES)

    # Timestamps
    pr_created_at = models.DateTimeField(null=True, blank=True)
    merged_at = models.DateTimeField(null=True, blank=True)
    first_review_at = models.DateTimeField(null=True, blank=True)

    # Calculated metrics
    cycle_time_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    review_time_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Size metrics
    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)

    # Flags
    is_revert = models.BooleanField(default=False)
    is_hotfix = models.BooleanField(default=False)

    # Sync tracking
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'github_pr_id', 'github_repo'],
                name='unique_team_pr'
            )
        ]
```

### PRReview
```python
class PRReview(BaseTeamModel):
    """GitHub PR Review."""

    STATE_CHOICES = [
        ('approved', 'Approved'),
        ('changes_requested', 'Changes Requested'),
        ('commented', 'Commented'),
    ]

    pull_request = models.ForeignKey(PullRequest, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True, related_name='reviews_given')
    state = models.CharField(max_length=20, choices=STATE_CHOICES)
    submitted_at = models.DateTimeField(null=True, blank=True)
```

### Commit
```python
class Commit(BaseTeamModel):
    """GitHub Commit."""

    github_sha = models.CharField(max_length=40)
    github_repo = models.CharField(max_length=255)
    author = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True, related_name='commits')
    message = models.TextField(blank=True)
    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)
    committed_at = models.DateTimeField(null=True, blank=True)
    pull_request = models.ForeignKey(PullRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='commits')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'github_sha'],
                name='unique_team_commit'
            )
        ]
```

### JiraIssue
```python
class JiraIssue(BaseTeamModel):
    """Jira Issue with sprint and story point tracking."""

    jira_key = models.CharField(max_length=50)  # e.g., PROJ-123
    jira_id = models.CharField(max_length=50)   # Jira's internal ID
    summary = models.TextField(blank=True)
    issue_type = models.CharField(max_length=50, blank=True)  # Story, Bug, Task, etc.
    status = models.CharField(max_length=50, blank=True)
    assignee = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True, related_name='jira_issues')
    story_points = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    sprint_id = models.CharField(max_length=50, blank=True)
    sprint_name = models.CharField(max_length=255, blank=True)

    # Timestamps
    issue_created_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Calculated
    cycle_time_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Sync tracking
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'jira_id'],
                name='unique_team_jira_issue'
            )
        ]
```

### AIUsageDaily
```python
class AIUsageDaily(BaseTeamModel):
    """Daily AI tool usage metrics (Copilot, Cursor, etc.)."""

    SOURCE_CHOICES = [
        ('copilot', 'GitHub Copilot'),
        ('cursor', 'Cursor'),
    ]

    member = models.ForeignKey(TeamMember, on_delete=models.CASCADE, related_name='ai_usage')
    date = models.DateField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)

    # Metrics
    active_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    suggestions_shown = models.IntegerField(default=0)
    suggestions_accepted = models.IntegerField(default=0)
    acceptance_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Sync tracking
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'member', 'date', 'source'],
                name='unique_team_member_date_source'
            )
        ]
```

### PRSurvey
```python
class PRSurvey(BaseTeamModel):
    """Survey for a Pull Request - tracks author's AI disclosure."""

    pull_request = models.OneToOneField(PullRequest, on_delete=models.CASCADE, related_name='survey')
    author = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True, related_name='authored_surveys')

    # Author response
    author_ai_assisted = models.BooleanField(null=True)  # null = not responded yet
    author_responded_at = models.DateTimeField(null=True, blank=True)
```

### PRSurveyReview
```python
class PRSurveyReview(BaseTeamModel):
    """Reviewer's response to a PR survey."""

    QUALITY_CHOICES = [
        (1, 'Could be better'),
        (2, 'OK'),
        (3, 'Super'),
    ]

    survey = models.ForeignKey(PRSurvey, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True, related_name='survey_reviews')

    # Reviewer responses
    quality_rating = models.IntegerField(choices=QUALITY_CHOICES, null=True)
    ai_guess = models.BooleanField(null=True)  # Did reviewer think it was AI-assisted?
    guess_correct = models.BooleanField(null=True)  # Calculated after author responds
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['survey', 'reviewer'],
                name='unique_survey_reviewer'
            )
        ]
```

### WeeklyMetrics
```python
class WeeklyMetrics(BaseTeamModel):
    """Pre-computed weekly metrics for dashboard performance."""

    member = models.ForeignKey(TeamMember, on_delete=models.CASCADE, related_name='weekly_metrics')
    week_start = models.DateField()  # Always a Monday

    # Delivery metrics
    prs_merged = models.IntegerField(default=0)
    avg_cycle_time_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg_review_time_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    commits_count = models.IntegerField(default=0)
    lines_added = models.IntegerField(default=0)
    lines_removed = models.IntegerField(default=0)

    # Quality metrics
    revert_count = models.IntegerField(default=0)
    hotfix_count = models.IntegerField(default=0)

    # Jira metrics
    story_points_completed = models.DecimalField(max_digits=10, decimal_places=1, default=0)
    issues_resolved = models.IntegerField(default=0)

    # AI metrics
    ai_assisted_prs = models.IntegerField(default=0)

    # Survey metrics
    avg_quality_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    surveys_completed = models.IntegerField(default=0)
    guess_accuracy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'member', 'week_start'],
                name='unique_team_member_week'
            )
        ]
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Model design changes later | Medium | Medium | Use TDD, design for extension |
| Migration conflicts | Low | High | Single dev, clean commits |
| Performance with large data | Medium | Medium | Add indexes, use select_related |
| User matching complexity | High | Medium | Keep TeamMember flexible |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| All models created | 9 models |
| Test coverage | > 90% |
| Migrations clean | No conflicts |
| Admin functional | All models visible |
| TDD compliance | All tests written first |

---

## Dependencies

### Internal
- `apps/teams/` - Team, BaseTeamModel, TeamScopedManager
- `apps/utils/` - BaseModel

### External (already installed)
- Django ORM
- PostgreSQL

### Environment
- No new environment variables needed

---

## Files to Create/Modify

### New Files
```
apps/metrics/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── migrations/
│   └── __init__.py
└── tests/
    ├── __init__.py
    └── test_models.py
```

### Modified Files
- `tformance/settings.py` - Add `apps.metrics` to INSTALLED_APPS
