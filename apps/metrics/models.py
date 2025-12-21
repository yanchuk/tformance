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
    body = models.TextField(
        blank=True,
        verbose_name="PR body",
        help_text="The description/body of the pull request",
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

    # Iteration metrics (calculated from synced data)
    review_rounds = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Review rounds",
        help_text="Number of review cycles (changes_requested → commits → re-review)",
    )
    avg_fix_response_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Avg fix response (hours)",
        help_text="Average time from review to next commit",
    )
    commits_after_first_review = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Commits after first review",
        help_text="Number of commits made after the first review",
    )
    total_comments = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Total comments",
        help_text="Total number of comments on this PR",
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

    # AI tracking
    is_ai_assisted = models.BooleanField(
        default=False,
        verbose_name="AI assisted",
        help_text="Whether AI tools were detected in this PR",
    )
    ai_tools_detected = models.JSONField(
        default=list,
        verbose_name="AI tools detected",
        help_text="List of AI tools detected (e.g., claude_code, copilot)",
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
    body = models.TextField(
        blank=True,
        verbose_name="Review body",
        help_text="The content of the review comment",
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Submitted at",
        help_text="When the review was submitted",
    )

    # AI tracking
    is_ai_review = models.BooleanField(
        default=False,
        verbose_name="AI review",
        help_text="Whether this review is from an AI bot",
    )
    ai_reviewer_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="AI reviewer type",
        help_text="Type of AI reviewer (e.g., coderabbit, copilot)",
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


class PRCheckRun(BaseTeamModel):
    """CI/CD check run for a pull request."""

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]

    CONCLUSION_CHOICES = [
        ("success", "Success"),
        ("failure", "Failure"),
        ("skipped", "Skipped"),
        ("cancelled", "Cancelled"),
        ("timed_out", "Timed Out"),
        ("action_required", "Action Required"),
        ("neutral", "Neutral"),
        ("stale", "Stale"),
    ]

    github_check_run_id = models.BigIntegerField(
        verbose_name="GitHub Check Run ID",
        help_text="The check run ID from GitHub",
    )
    pull_request = models.ForeignKey(
        PullRequest,
        on_delete=models.CASCADE,
        related_name="check_runs",
        verbose_name="Pull request",
        help_text="The PR this check run belongs to",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Check name",
        help_text="Name of the check (e.g., pytest, eslint, build)",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name="Status",
        help_text="Current status of the check run",
    )
    conclusion = models.CharField(
        max_length=20,
        choices=CONCLUSION_CHOICES,
        null=True,
        blank=True,
        verbose_name="Conclusion",
        help_text="Final conclusion of the check run",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Started at",
        help_text="When the check run started",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Completed at",
        help_text="When the check run completed",
    )
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Duration (seconds)",
        help_text="How long the check run took",
    )

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "PR Check Run"
        verbose_name_plural = "PR Check Runs"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_check_run_id"],
                name="unique_team_check_run",
            )
        ]
        indexes = [
            models.Index(fields=["pull_request", "name"], name="check_run_pr_name_idx"),
            models.Index(fields=["started_at"], name="check_run_started_at_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.conclusion or self.status})"


class PRFile(BaseTeamModel):
    """File changed in a pull request."""

    STATUS_CHOICES = [
        ("added", "Added"),
        ("modified", "Modified"),
        ("removed", "Removed"),
        ("renamed", "Renamed"),
    ]

    CATEGORY_CHOICES = [
        ("frontend", "Frontend"),
        ("backend", "Backend"),
        ("test", "Test"),
        ("docs", "Documentation"),
        ("config", "Configuration"),
        ("other", "Other"),
    ]

    pull_request = models.ForeignKey(
        PullRequest,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Pull request",
        help_text="The PR this file belongs to",
    )
    filename = models.CharField(
        max_length=500,
        verbose_name="Filename",
        help_text="Path to the file",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name="Status",
        help_text="File change status",
    )
    additions = models.IntegerField(
        default=0,
        verbose_name="Additions",
        help_text="Lines added",
    )
    deletions = models.IntegerField(
        default=0,
        verbose_name="Deletions",
        help_text="Lines deleted",
    )
    changes = models.IntegerField(
        default=0,
        verbose_name="Changes",
        help_text="Total changes",
    )
    file_category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        verbose_name="File category",
        help_text="Categorized file type",
    )

    class Meta:
        ordering = ["filename"]
        verbose_name = "PR File"
        verbose_name_plural = "PR Files"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "pull_request", "filename"],
                name="unique_team_pr_file",
            )
        ]
        indexes = [
            models.Index(fields=["pull_request", "file_category"], name="pr_file_category_idx"),
        ]

    @staticmethod
    def categorize_file(filename: str) -> str:
        """Categorize file based on extension and path."""
        filename_lower = filename.lower()

        # Test files (check first - may have .py extension)
        if "test" in filename_lower or "spec" in filename_lower:
            return "test"

        # Frontend
        if filename_lower.endswith((".tsx", ".jsx", ".vue", ".css", ".scss", ".html")):
            return "frontend"

        # Backend
        if filename_lower.endswith((".py", ".go", ".java", ".rb", ".rs")):
            return "backend"

        # Docs
        if filename_lower.endswith((".md", ".rst", ".txt")):
            return "docs"

        # Config
        if filename_lower.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".env")):
            return "config"

        return "other"

    def __str__(self):
        return f"{self.filename} ({self.file_category})"


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

    # AI tracking
    is_ai_assisted = models.BooleanField(
        default=False,
        verbose_name="AI assisted",
        help_text="Whether AI co-authors were detected in this commit",
    )
    ai_co_authors = models.JSONField(
        default=list,
        verbose_name="AI co-authors",
        help_text="List of AI co-authors detected (e.g., claude, copilot)",
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


class PRComment(BaseTeamModel):
    """
    A comment on a pull request.

    Tracks both issue comments (general PR comments) and review comments
    (inline code comments).
    """

    COMMENT_TYPE_CHOICES = [
        ("issue", "Issue Comment"),
        ("review", "Review Comment"),
    ]

    github_comment_id = models.BigIntegerField(
        verbose_name="GitHub Comment ID",
        help_text="The comment ID from GitHub",
    )
    pull_request = models.ForeignKey(
        PullRequest,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Pull request",
        help_text="The PR this comment belongs to",
    )
    author = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pr_comments",
        verbose_name="Author",
        help_text="The team member who created the comment",
    )
    body = models.TextField(
        verbose_name="Comment body",
        help_text="The text content of the comment",
    )
    comment_type = models.CharField(
        max_length=20,
        choices=COMMENT_TYPE_CHOICES,
        verbose_name="Comment type",
        help_text="Whether this is an issue comment or review comment",
    )

    # Review comment specific fields
    path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="File path",
        help_text="File path for review comments",
    )
    line = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Line number",
        help_text="Line number for review comments",
    )

    # Threading
    in_reply_to_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="In reply to",
        help_text="GitHub comment ID this is replying to (for threaded comments)",
    )

    # Timestamps
    comment_created_at = models.DateTimeField(
        verbose_name="Comment created at",
        help_text="When the comment was created on GitHub",
    )
    comment_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Comment updated at",
        help_text="When the comment was last updated on GitHub",
    )

    class Meta:
        ordering = ["-comment_created_at"]
        verbose_name = "PR Comment"
        verbose_name_plural = "PR Comments"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_comment_id"],
                name="unique_team_pr_comment",
            )
        ]
        indexes = [
            models.Index(fields=["pull_request", "comment_created_at"], name="pr_comment_pr_created_idx"),
            models.Index(fields=["author", "comment_type"], name="pr_comment_author_type_idx"),
        ]

    def __str__(self):
        return f"Comment {self.github_comment_id} on PR #{self.pull_request.github_pr_id}"


class Deployment(BaseTeamModel):
    """
    A deployment from GitHub.

    Tracks deployment events to production and staging environments,
    including status, creator, and associated pull requests.
    """

    STATUS_CHOICES = [
        ("success", "Success"),
        ("failure", "Failure"),
        ("pending", "Pending"),
        ("error", "Error"),
    ]

    ENVIRONMENT_CHOICES = [
        ("production", "Production"),
        ("staging", "Staging"),
    ]

    github_deployment_id = models.BigIntegerField(
        verbose_name="GitHub Deployment ID",
        help_text="The deployment ID from GitHub",
    )
    github_repo = models.CharField(
        max_length=255,
        verbose_name="GitHub repository",
        help_text="Repository name (e.g., 'owner/repo')",
    )
    environment = models.CharField(
        max_length=100,
        choices=ENVIRONMENT_CHOICES,
        verbose_name="Environment",
        help_text="Deployment environment",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name="Status",
        help_text="Deployment status",
    )
    creator = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deployments",
        verbose_name="Creator",
        help_text="The team member who created the deployment",
    )
    deployed_at = models.DateTimeField(
        verbose_name="Deployed at",
        help_text="When the deployment occurred",
    )
    pull_request = models.ForeignKey(
        PullRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deployments",
        verbose_name="Pull request",
        help_text="The PR associated with this deployment",
    )
    sha = models.CharField(
        max_length=40,
        verbose_name="Git SHA",
        help_text="The commit SHA deployed",
    )

    class Meta:
        ordering = ["-deployed_at"]
        verbose_name = "Deployment"
        verbose_name_plural = "Deployments"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_deployment_id"],
                name="unique_team_deployment",
            )
        ]
        indexes = [
            models.Index(fields=["github_repo", "environment"], name="deployment_repo_env_idx"),
            models.Index(fields=["deployed_at"], name="deployment_deployed_at_idx"),
            models.Index(fields=["status"], name="deployment_status_idx"),
            models.Index(fields=["pull_request"], name="deployment_pr_idx"),
            models.Index(fields=["creator", "status"], name="deployment_creator_status_idx"),
        ]

    def __str__(self):
        return f"{self.github_repo} - {self.environment}"


class ReviewerCorrelation(BaseTeamModel):
    """
    Tracks agreement/disagreement patterns between pairs of reviewers.

    Used to identify:
    - Redundant reviewer pairings (always agree, adding one to both doesn't add value)
    - Complementary reviewers (different perspectives, catch different issues)
    """

    # Reviewer pair
    reviewer_1 = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name="correlations_as_reviewer_1",
        verbose_name="Reviewer 1",
        help_text="First reviewer in the pair",
    )
    reviewer_2 = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name="correlations_as_reviewer_2",
        verbose_name="Reviewer 2",
        help_text="Second reviewer in the pair",
    )

    # Statistics
    prs_reviewed_together = models.IntegerField(
        default=0,
        verbose_name="PRs reviewed together",
        help_text="Number of PRs where both reviewers submitted reviews",
    )
    agreements = models.IntegerField(
        default=0,
        verbose_name="Agreements",
        help_text="Number of PRs where both approved or both requested changes",
    )
    disagreements = models.IntegerField(
        default=0,
        verbose_name="Disagreements",
        help_text="Number of PRs where one approved and the other requested changes",
    )

    # Thresholds for redundancy detection
    REDUNDANCY_THRESHOLD = 95  # 95% agreement rate
    MIN_SAMPLE_SIZE = 10  # Minimum PRs reviewed together

    class Meta:
        ordering = ["-prs_reviewed_together"]
        verbose_name = "Reviewer Correlation"
        verbose_name_plural = "Reviewer Correlations"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "reviewer_1", "reviewer_2"],
                name="unique_team_reviewer_pair",
            )
        ]
        indexes = [
            models.Index(fields=["reviewer_1", "reviewer_2"], name="correlation_pair_idx"),
            models.Index(fields=["prs_reviewed_together"], name="correlation_count_idx"),
        ]

    @property
    def agreement_rate(self):
        """Calculate agreement rate as a percentage."""
        from decimal import Decimal

        if self.prs_reviewed_together == 0:
            return Decimal("0.00")
        rate = (self.agreements / self.prs_reviewed_together) * 100
        return Decimal(str(round(rate, 2)))

    @property
    def is_redundant(self):
        """Check if this reviewer pair is potentially redundant.

        A pair is considered redundant if:
        - They have reviewed at least MIN_SAMPLE_SIZE PRs together
        - Their agreement rate is >= REDUNDANCY_THRESHOLD
        """
        return self.prs_reviewed_together >= self.MIN_SAMPLE_SIZE and self.agreement_rate >= self.REDUNDANCY_THRESHOLD

    def __str__(self):
        return f"{self.reviewer_1.display_name} ↔ {self.reviewer_2.display_name}: {self.agreement_rate:.2f}% agreement"


class DailyInsight(BaseTeamModel):
    """
    Daily generated insights about team metrics.

    Tracks trends, anomalies, comparisons, and recommended actions based on team data.
    """

    CATEGORY_CHOICES = [
        ("trend", "Trend"),
        ("anomaly", "Anomaly"),
        ("comparison", "Comparison"),
        ("action", "Action"),
    ]

    PRIORITY_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    date = models.DateField(
        db_index=True,
        verbose_name="Date",
        help_text="Date this insight was generated for",
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name="Category",
        help_text="Type of insight (trend, anomaly, comparison, action)",
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        verbose_name="Priority",
        help_text="Priority level of this insight",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Brief title of the insight",
    )
    description = models.TextField(
        verbose_name="Description",
        help_text="Detailed description of the insight",
    )
    metric_type = models.CharField(
        max_length=100,
        verbose_name="Metric Type",
        help_text="Type of metric this insight is about (e.g., cycle_time, review_time)",
    )
    metric_value = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Metric Value",
        help_text="JSON data containing metric values and context",
    )
    comparison_period = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Comparison Period",
        help_text="Time period for comparison (e.g., week_over_week, month_over_month)",
    )
    is_dismissed = models.BooleanField(
        default=False,
        verbose_name="Is Dismissed",
        help_text="Whether this insight has been dismissed by the user",
    )
    dismissed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dismissed At",
        help_text="When this insight was dismissed",
    )

    class Meta:
        ordering = ["-date", "priority", "category"]
        verbose_name = "Daily Insight"
        verbose_name_plural = "Daily Insights"
        indexes = [
            models.Index(fields=["date", "category"], name="insight_date_cat_idx"),
            models.Index(fields=["priority", "is_dismissed"], name="insight_pri_dismissed_idx"),
        ]

    def __str__(self):
        return f"{self.date} - {self.title}"
