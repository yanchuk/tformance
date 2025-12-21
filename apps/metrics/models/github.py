"""GitHub-related models: PullRequest, PRReview, PRCheckRun, PRFile, PRComment, Commit."""

from django.db import models

from apps.teams.models import BaseTeamModel

from .team import TeamMember


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
