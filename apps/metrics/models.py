from django.db import models

from apps.teams.models import BaseTeamModel


class TeamMember(BaseTeamModel):
    """
    A team member representing a developer or team member across various integrations.

    This model unifies identity across GitHub, Jira, and Slack to track a single
    developer's metrics and performance across all integrated tools.
    """

    email = models.EmailField(
        blank=True,
        verbose_name="Email address",
        help_text="Team member's email address",
    )
    display_name = models.CharField(
        max_length=255,
        verbose_name="Display name",
        help_text="How this team member's name is displayed",
    )

    # Integration identities
    github_username = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name="GitHub username",
        help_text="GitHub username for this team member",
    )
    github_id = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        verbose_name="GitHub ID",
        help_text="GitHub user ID for this team member",
    )
    jira_account_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name="Jira account ID",
        help_text="Jira account ID for this team member",
    )
    slack_user_id = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        verbose_name="Slack user ID",
        help_text="Slack user ID for this team member",
    )

    # Role
    ROLE_CHOICES = [
        ("developer", "Developer"),
        ("lead", "Lead"),
        ("admin", "Admin"),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="developer",
        verbose_name="Role",
        help_text="Team member's role",
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active status",
        help_text="Whether this team member is currently active",
    )

    class Meta:
        ordering = ["display_name"]
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_id"],
                condition=models.Q(github_id__gt=""),
                name="unique_team_github_id",
            ),
            models.UniqueConstraint(
                fields=["team", "email"],
                condition=models.Q(email__gt=""),
                name="unique_team_email",
            ),
        ]

    def __str__(self):
        return self.display_name


class PullRequest(BaseTeamModel):
    """
    A pull request from GitHub.

    Tracks PR metrics including cycle time, review time, and state.
    """

    STATE_CHOICES = [
        ("open", "Open"),
        ("merged", "Merged"),
        ("closed", "Closed"),
    ]

    # GitHub identifiers
    github_pr_id = models.BigIntegerField(
        verbose_name="GitHub PR ID",
        help_text="The PR number from GitHub",
    )
    github_repo = models.CharField(
        max_length=255,
        verbose_name="GitHub repository",
        help_text="Repository name (e.g., 'owner/repo')",
    )

    # PR metadata
    title = models.TextField(
        blank=True,
        verbose_name="PR title",
        help_text="The title of the pull request",
    )
    author = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pull_requests",
        verbose_name="Author",
        help_text="The team member who created the PR",
    )
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        verbose_name="State",
        help_text="Current state of the PR",
    )

    # Timestamps
    pr_created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="PR created at",
        help_text="When the PR was created",
    )
    merged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Merged at",
        help_text="When the PR was merged",
    )
    first_review_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="First review at",
        help_text="When the first review was submitted",
    )

    # Metrics
    cycle_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cycle time (hours)",
        help_text="Time from PR creation to merge",
    )
    review_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Review time (hours)",
        help_text="Time from PR creation to first review",
    )

    # Code changes
    additions = models.IntegerField(
        default=0,
        verbose_name="Additions",
        help_text="Lines added in this PR",
    )
    deletions = models.IntegerField(
        default=0,
        verbose_name="Deletions",
        help_text="Lines deleted in this PR",
    )

    # Flags
    is_revert = models.BooleanField(
        default=False,
        verbose_name="Is revert",
        help_text="Whether this is a revert PR",
    )
    is_hotfix = models.BooleanField(
        default=False,
        verbose_name="Is hotfix",
        help_text="Whether this is a hotfix PR",
    )

    # Jira integration
    jira_key = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        default="",
        verbose_name="Jira Key",
        help_text="Extracted Jira issue key from PR title or branch (e.g., PROJ-123)",
    )

    # Sync tracking
    synced_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Synced at",
        help_text="Last time this PR data was synced",
    )

    class Meta:
        ordering = ["-pr_created_at"]
        verbose_name = "Pull Request"
        verbose_name_plural = "Pull Requests"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_pr_id", "github_repo"],
                name="unique_team_pr",
            )
        ]
        indexes = [
            models.Index(fields=["github_repo", "state"], name="pr_repo_state_idx"),
            models.Index(fields=["author", "state"], name="pr_author_state_idx"),
            models.Index(fields=["merged_at"], name="pr_merged_at_idx"),
            models.Index(fields=["pr_created_at"], name="pr_created_at_idx"),
        ]

    def __str__(self):
        title_part = f" {self.title[:50]}" if self.title else ""
        return f"{self.github_repo}#{self.github_pr_id}{title_part}"


class PRReview(BaseTeamModel):
    """
    A review on a pull request.

    Tracks who reviewed the PR and what their review state was.
    """

    STATE_CHOICES = [
        ("approved", "Approved"),
        ("changes_requested", "Changes Requested"),
        ("commented", "Commented"),
    ]

    # GitHub identifier
    github_review_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="GitHub Review ID",
        help_text="The review ID from GitHub",
    )

    # Relationships
    pull_request = models.ForeignKey(
        PullRequest,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Pull request",
        help_text="The PR being reviewed",
    )
    reviewer = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reviews_given",
        verbose_name="Reviewer",
        help_text="The team member who submitted the review",
    )

    # Review details
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        verbose_name="State",
        help_text="The review state",
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Submitted at",
        help_text="When the review was submitted",
    )

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "PR Review"
        verbose_name_plural = "PR Reviews"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_review_id"],
                condition=models.Q(github_review_id__isnull=False),
                name="unique_team_review",
            )
        ]
        indexes = [
            models.Index(fields=["pull_request", "submitted_at"], name="review_pr_submitted_idx"),
            models.Index(fields=["reviewer", "state"], name="review_reviewer_state_idx"),
        ]

    def __str__(self):
        return f"Review on #{self.pull_request.github_pr_id} by {self.reviewer}"


class Commit(BaseTeamModel):
    """
    A Git commit from GitHub.

    Tracks individual commits and their metadata.
    """

    # GitHub identifiers
    github_sha = models.CharField(
        max_length=40,
        verbose_name="GitHub SHA",
        help_text="The commit SHA from GitHub",
    )
    github_repo = models.CharField(
        max_length=255,
        verbose_name="GitHub repository",
        help_text="Repository name (e.g., 'owner/repo')",
    )

    # Commit metadata
    author = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="commits",
        verbose_name="Author",
        help_text="The team member who authored the commit",
    )
    message = models.TextField(
        blank=True,
        verbose_name="Commit message",
        help_text="The commit message",
    )
    committed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Committed at",
        help_text="When the commit was made",
    )

    # Code changes
    additions = models.IntegerField(
        default=0,
        verbose_name="Additions",
        help_text="Lines added in this commit",
    )
    deletions = models.IntegerField(
        default=0,
        verbose_name="Deletions",
        help_text="Lines deleted in this commit",
    )

    # Relationships
    pull_request = models.ForeignKey(
        PullRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commits",
        verbose_name="Pull request",
        help_text="The PR this commit belongs to",
    )

    class Meta:
        ordering = ["-committed_at"]
        verbose_name = "Commit"
        verbose_name_plural = "Commits"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_sha"],
                name="unique_team_commit",
            )
        ]
        indexes = [
            models.Index(fields=["github_repo", "committed_at"], name="commit_repo_date_idx"),
            models.Index(fields=["author", "committed_at"], name="commit_author_date_idx"),
            models.Index(fields=["pull_request"], name="commit_pr_idx"),
        ]

    def __str__(self):
        return f"{self.github_sha[:7]} - {self.message[:50] if self.message else ''}"


class JiraIssue(BaseTeamModel):
    """
    A Jira issue from the team's Jira workspace.

    Tracks sprint assignments, story points, and cycle time for planning metrics.
    """

    # Jira identifiers
    jira_key = models.CharField(
        max_length=50,
        verbose_name="Jira Key",
        help_text="e.g., PROJ-123",
    )
    jira_id = models.CharField(
        max_length=50,
        verbose_name="Jira ID",
        help_text="Jira's internal ID",
    )

    # Issue details
    summary = models.TextField(
        blank=True,
        verbose_name="Summary",
        help_text="Issue summary/title",
    )
    issue_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Issue Type",
        help_text="Story, Bug, Task, etc.",
    )
    status = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Status",
        help_text="Current issue status",
    )
    assignee = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jira_issues",
        verbose_name="Assignee",
        help_text="The team member assigned to this issue",
    )

    # Sprint and estimation
    story_points = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="Story Points",
        help_text="Estimated story points",
    )
    sprint_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Sprint ID",
        help_text="The sprint this issue belongs to",
    )
    sprint_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Sprint Name",
        help_text="Human-readable sprint name",
    )

    # Timestamps
    issue_created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Created At",
        help_text="When the issue was created in Jira",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Resolved At",
        help_text="When the issue was resolved",
    )

    # Calculated metrics
    cycle_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cycle Time (hours)",
        help_text="Time from creation to resolution",
    )

    # Sync tracking
    synced_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Synced at",
        help_text="Last time this issue data was synced",
    )

    class Meta:
        ordering = ["-issue_created_at"]
        verbose_name = "Jira Issue"
        verbose_name_plural = "Jira Issues"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "jira_id"],
                name="unique_team_jira_issue",
            )
        ]
        indexes = [
            models.Index(fields=["jira_key"], name="jira_issue_key_idx"),
            models.Index(fields=["resolved_at"], name="jira_resolved_at_idx"),
            models.Index(fields=["assignee", "status"], name="jira_assignee_status_idx"),
            models.Index(fields=["sprint_id"], name="jira_sprint_idx"),
        ]

    def __str__(self):
        return self.jira_key

    @property
    def related_prs(self):
        """Get all PRs that reference this Jira issue via jira_key."""
        return PullRequest.objects.filter(team=self.team, jira_key=self.jira_key)


class AIUsageDaily(BaseTeamModel):
    """Daily AI tool usage metrics (Copilot, Cursor, etc.)."""

    SOURCE_CHOICES = [
        ("copilot", "GitHub Copilot"),
        ("cursor", "Cursor"),
    ]

    member = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name="ai_usage",
        verbose_name="Team Member",
        help_text="The team member who used the AI tool",
    )
    date = models.DateField(
        verbose_name="Date",
        help_text="The date for this usage record",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        verbose_name="Source",
        help_text="AI tool source (Copilot, Cursor, etc.)",
    )

    active_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Active Hours",
        help_text="Hours the AI tool was active",
    )
    suggestions_shown = models.IntegerField(
        default=0,
        verbose_name="Suggestions Shown",
        help_text="Number of AI suggestions shown",
    )
    suggestions_accepted = models.IntegerField(
        default=0,
        verbose_name="Suggestions Accepted",
        help_text="Number of AI suggestions accepted",
    )
    acceptance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Acceptance Rate",
        help_text="Percentage of suggestions accepted",
    )

    synced_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Synced at",
        help_text="Last time this usage data was synced",
    )

    class Meta:
        ordering = ["-date", "member"]
        verbose_name = "AI Usage Daily"
        verbose_name_plural = "AI Usage Daily"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "member", "date", "source"],
                name="unique_team_member_date_source",
            )
        ]
        indexes = [
            models.Index(fields=["date"], name="ai_usage_date_idx"),
            models.Index(fields=["member", "date"], name="ai_usage_member_date_idx"),
            models.Index(fields=["source", "date"], name="ai_usage_source_date_idx"),
        ]

    def __str__(self):
        return f"{self.member} - {self.source} - {self.date}"


class PRSurvey(BaseTeamModel):
    """Survey for a Pull Request - tracks author's AI disclosure."""

    pull_request = models.OneToOneField(
        PullRequest,
        on_delete=models.CASCADE,
        related_name="survey",
        verbose_name="Pull Request",
        help_text="The PR this survey is for",
    )
    author = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="authored_surveys",
        verbose_name="Author",
        help_text="The PR author",
    )

    # Token fields for survey access
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        verbose_name="Token",
        help_text="Unique token for accessing the survey via URL",
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Token Expires At",
        help_text="When the survey token expires (typically 7 days after creation)",
    )
    github_comment_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="GitHub Comment ID",
        help_text="The GitHub comment ID where the survey was posted",
    )

    author_ai_assisted = models.BooleanField(
        null=True,
        verbose_name="Author AI Assisted",
        help_text="Whether the author used AI tools (null = not responded yet)",
    )
    author_responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Author Responded At",
        help_text="When the author responded to the survey",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "PR Survey"
        verbose_name_plural = "PR Surveys"
        indexes = [
            models.Index(fields=["pull_request"], name="pr_survey_pr_idx"),
            models.Index(fields=["author", "author_ai_assisted"], name="pr_survey_author_ai_idx"),
            models.Index(fields=["author_responded_at"], name="pr_survey_responded_idx"),
        ]

    def __str__(self):
        return f"Survey for PR #{self.pull_request.github_pr_id}"

    def is_token_expired(self):
        """Check if the survey token has expired."""
        if self.token_expires_at is None:
            return True
        from django.utils import timezone

        return self.token_expires_at < timezone.now()

    def has_author_responded(self) -> bool:
        """Check if the author has responded to the survey.

        The author_ai_assisted field starts as None and becomes a boolean (True/False)
        once the author responds. This method checks if it's been set to a boolean value.

        Returns:
            bool: True if the author has responded, False otherwise
        """
        return isinstance(self.author_ai_assisted, bool)


class PRSurveyReview(BaseTeamModel):
    """Reviewer's response to a PR survey."""

    QUALITY_CHOICES = [
        (1, "Could be better"),
        (2, "OK"),
        (3, "Super"),
    ]

    survey = models.ForeignKey(
        PRSurvey,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Survey",
        help_text="The survey this review is for",
    )
    reviewer = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="survey_reviews",
        verbose_name="Reviewer",
        help_text="The reviewer providing feedback",
    )

    quality_rating = models.IntegerField(
        choices=QUALITY_CHOICES,
        null=True,
        verbose_name="Quality Rating",
        help_text="Reviewer's quality rating of the PR",
    )
    ai_guess = models.BooleanField(
        null=True,
        verbose_name="AI Guess",
        help_text="Reviewer's guess whether AI was used",
    )
    guess_correct = models.BooleanField(
        null=True,
        verbose_name="Guess Correct",
        help_text="Whether the reviewer's guess was correct",
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Responded At",
        help_text="When the reviewer responded",
    )

    class Meta:
        ordering = ["-responded_at"]
        verbose_name = "PR Survey Review"
        verbose_name_plural = "PR Survey Reviews"
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "reviewer"],
                name="unique_survey_reviewer",
            )
        ]
        indexes = [
            models.Index(fields=["survey", "responded_at"], name="pr_survey_review_survey_idx"),
            models.Index(fields=["reviewer", "responded_at"], name="pr_survey_review_reviewer_idx"),
            models.Index(fields=["quality_rating"], name="pr_survey_review_quality_idx"),
        ]

    def __str__(self):
        reviewer_name = self.reviewer.display_name if self.reviewer else "Unknown"
        return f"Review by {reviewer_name} on Survey #{self.survey.pull_request.github_pr_id}"


class WeeklyMetrics(BaseTeamModel):
    """
    Pre-computed weekly metrics for dashboard performance.

    Aggregates metrics by team member and week for efficient dashboard queries.
    """

    member = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name="weekly_metrics",
        verbose_name="Team Member",
        help_text="The team member these metrics belong to",
    )
    week_start = models.DateField(
        verbose_name="Week Start",
        help_text="Monday of the week",
    )

    # Delivery metrics
    prs_merged = models.IntegerField(
        default=0,
        verbose_name="PRs Merged",
        help_text="Number of PRs merged this week",
    )
    avg_cycle_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Avg Cycle Time (hours)",
        help_text="Average time from PR creation to merge",
    )
    avg_review_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Avg Review Time (hours)",
        help_text="Average time from PR creation to first review",
    )
    commits_count = models.IntegerField(
        default=0,
        verbose_name="Commits",
        help_text="Number of commits made this week",
    )
    lines_added = models.IntegerField(
        default=0,
        verbose_name="Lines Added",
        help_text="Total lines added this week",
    )
    lines_removed = models.IntegerField(
        default=0,
        verbose_name="Lines Removed",
        help_text="Total lines removed this week",
    )

    # Quality metrics
    revert_count = models.IntegerField(
        default=0,
        verbose_name="Reverts",
        help_text="Number of revert PRs this week",
    )
    hotfix_count = models.IntegerField(
        default=0,
        verbose_name="Hotfixes",
        help_text="Number of hotfix PRs this week",
    )

    # Jira metrics
    story_points_completed = models.DecimalField(
        max_digits=10,
        decimal_places=1,
        default=0,
        verbose_name="Story Points",
        help_text="Total story points completed this week",
    )
    issues_resolved = models.IntegerField(
        default=0,
        verbose_name="Issues Resolved",
        help_text="Number of Jira issues resolved this week",
    )

    # AI metrics
    ai_assisted_prs = models.IntegerField(
        default=0,
        verbose_name="AI-Assisted PRs",
        help_text="Number of PRs created with AI assistance",
    )

    # Survey metrics
    avg_quality_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Avg Quality Rating",
        help_text="Average quality rating from PR surveys",
    )
    surveys_completed = models.IntegerField(
        default=0,
        verbose_name="Surveys Completed",
        help_text="Number of PR surveys completed this week",
    )
    guess_accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Guess Accuracy (%)",
        help_text="Percentage of correct AI usage guesses by reviewers",
    )

    class Meta:
        ordering = ["-week_start", "member"]
        verbose_name = "Weekly Metrics"
        verbose_name_plural = "Weekly Metrics"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "member", "week_start"],
                name="unique_team_member_week",
            )
        ]
        indexes = [
            models.Index(fields=["week_start"], name="weekly_metrics_week_idx"),
            models.Index(fields=["member", "week_start"], name="weekly_metrics_member_week_idx"),
        ]

    def __str__(self):
        return f"{self.member} - Week of {self.week_start}"
