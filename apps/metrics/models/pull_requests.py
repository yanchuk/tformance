"""PullRequest model - core PR entity from GitHub."""

from django.contrib.postgres.indexes import GinIndex
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
    is_draft = models.BooleanField(
        default=False,
        verbose_name="Is draft",
        help_text="Whether this PR is a draft",
    )

    # GitHub metadata (store all data from API)
    labels = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Labels",
        help_text="List of label names from GitHub",
    )
    milestone_title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Milestone title",
        help_text="GitHub milestone title if assigned",
    )
    assignees = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Assignees",
        help_text="List of assignee usernames from GitHub",
    )
    linked_issues = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Linked issues",
        help_text="List of linked issue numbers from GitHub",
    )

    # AI tracking
    is_ai_assisted = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name="AI assisted",
        help_text="Whether AI tools were detected in this PR (None = not yet processed)",
    )
    ai_tools_detected = models.JSONField(
        default=list,
        verbose_name="AI tools detected",
        help_text="List of AI tools detected (e.g., claude_code, copilot)",
    )
    ai_detection_version = models.CharField(
        max_length=10,
        blank=True,
        default="",
        verbose_name="AI detection version",
        help_text="Pattern version used for AI detection (e.g., 1.5.0)",
    )

    # LLM-generated summary (from Groq/Llama analysis)
    llm_summary = models.JSONField(
        null=True,
        blank=True,
        verbose_name="LLM summary",
        help_text="AI-generated PR summary with tech detection and description",
    )
    llm_summary_version = models.CharField(
        max_length=10,
        blank=True,
        default="",
        verbose_name="LLM summary version",
        help_text="Prompt version used for LLM summary (e.g., 5.0.0)",
    )

    # Aggregated AI signals (from commits, reviews, files)
    has_ai_commits = models.BooleanField(
        default=False,
        verbose_name="Has AI commits",
        help_text="True if any commit has AI co-authors or is_ai_assisted",
    )
    has_ai_review = models.BooleanField(
        default=False,
        verbose_name="Has AI review",
        help_text="True if any review is from an AI reviewer",
    )
    has_ai_files = models.BooleanField(
        default=False,
        verbose_name="Has AI config files",
        help_text="True if PR modifies AI config files (.cursorrules, CLAUDE.md, etc.)",
    )

    # Composite AI scoring (Phase 5)
    ai_confidence_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="AI confidence score",
        help_text="Weighted score (0.000-1.000) combining all AI detection signals",
    )
    ai_signals = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="AI signal breakdown",
        help_text="Detailed breakdown of each detection signal source",
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
            # Composite indexes for dashboard queries (added for performance)
            models.Index(fields=["team", "state", "merged_at"], name="pr_team_state_merged_idx"),
            models.Index(fields=["team", "author", "merged_at"], name="pr_team_author_merged_idx"),
            models.Index(fields=["team", "pr_created_at"], name="pr_team_created_idx"),
            # GIN indexes for JSONB fields - faster queries on AI tools and LLM summary
            # Note: These indexes already exist from migration 0020 (created via raw SQL)
            # Adding to Meta ensures Django tracks them and they're recreated on fresh DBs
            GinIndex(fields=["ai_tools_detected"], name="pr_llm_ai_tools_gin_idx", opclasses=["jsonb_path_ops"]),
            GinIndex(fields=["llm_summary"], name="pr_llm_summary_gin_idx", opclasses=["jsonb_path_ops"]),
        ]

    def __str__(self):
        title_part = f" {self.title[:50]}" if self.title else ""
        return f"{self.github_repo}#{self.github_pr_id}{title_part}"

    @property
    def github_url(self):
        """Construct GitHub URL for this PR."""
        return f"https://github.com/{self.github_repo}/pull/{self.github_pr_id}"

    @property
    def effective_tech_categories(self) -> list[str]:
        """Get technology categories with LLM priority over pattern-based detection.

        Priority order:
        1. LLM-detected categories from llm_summary.tech.categories (more accurate)
        2. Pattern-based categories from PRFile annotations (fallback)

        Returns:
            List of technology category strings (e.g., ['backend', 'frontend', 'devops'])
        """
        # Check LLM categories first (higher accuracy)
        if self.llm_summary:
            llm_cats = self.llm_summary.get("tech", {}).get("categories", [])
            if llm_cats:
                return llm_cats

        # Fallback to pattern-based categories (from annotation or related files)
        if hasattr(self, "tech_categories") and self.tech_categories:
            return self.tech_categories

        # Final fallback: aggregate from related PRFile records
        return list(
            self.files.exclude(file_category="")
            .exclude(file_category__isnull=True)
            .values_list("file_category", flat=True)
            .distinct()
        )

    @property
    def effective_is_ai_assisted(self) -> bool:
        """Get AI assistance status with LLM priority over regex pattern detection.

        Priority order:
        1. LLM detection from llm_summary.ai.is_assisted (more accurate, context-aware)
        2. Regex pattern detection from is_ai_assisted field (fallback)

        Returns:
            True if AI tools were used in creating this PR
        """
        # Check LLM detection first (higher accuracy)
        if self.llm_summary:
            ai_data = self.llm_summary.get("ai", {})
            # Only use LLM result if confidence is reasonable (>= 0.5)
            if ai_data.get("is_assisted") is not None and ai_data.get("confidence", 0) >= 0.5:
                return ai_data["is_assisted"]

        # Fallback to regex pattern detection
        return self.is_ai_assisted

    @property
    def effective_ai_tools(self) -> list[str]:
        """Get detected AI tools with LLM priority over regex pattern detection.

        Priority order:
        1. LLM detection from llm_summary.ai.tools (more accurate)
        2. Regex pattern detection from ai_tools_detected field (fallback)

        Returns:
            List of AI tool identifiers (e.g., ['cursor', 'claude', 'copilot'])
        """
        # Check LLM detection first (higher accuracy)
        if self.llm_summary:
            llm_tools = self.llm_summary.get("ai", {}).get("tools", [])
            if llm_tools:
                return llm_tools

        # Fallback to regex pattern detection
        return self.ai_tools_detected or []

    @property
    def ai_code_tools(self) -> list[str]:
        """Get AI tools that help write/generate code.

        Returns:
            List of code-category AI tools (e.g., ['cursor', 'copilot'])
        """
        from apps.metrics.services.ai_categories import categorize_tools

        categorized = categorize_tools(self.effective_ai_tools)
        return categorized.get("code", [])

    @property
    def ai_review_tools(self) -> list[str]:
        """Get AI tools that review/comment on code.

        Returns:
            List of review-category AI tools (e.g., ['coderabbit', 'cubic'])
        """
        from apps.metrics.services.ai_categories import categorize_tools

        categorized = categorize_tools(self.effective_ai_tools)
        return categorized.get("review", [])

    @property
    def ai_category(self) -> str | None:
        """Get the dominant AI assistance category for this PR.

        Returns:
            "code" | "review" | "both" | None

        Categories:
            - code: AI tools that write/generate code (Cursor, Copilot, etc.)
            - review: AI tools that review/comment on code (CodeRabbit, etc.)
            - both: PR uses both code and review AI tools
            - None: No AI tools detected or all tools excluded
        """
        from apps.metrics.services.ai_categories import get_ai_category

        return get_ai_category(self.effective_ai_tools)

    @property
    def effective_pr_type(self) -> str:
        """Get PR type from LLM summary or infer from labels.

        Priority order:
        1. LLM detection from llm_summary.summary.type (most accurate)
        2. Inferred from labels (bugfix, feature, etc.)
        3. Default to 'unknown'

        Returns:
            PR type string: feature, bugfix, refactor, docs, test, chore, ci, unknown
        """
        valid_types = {"feature", "bugfix", "refactor", "docs", "test", "chore", "ci"}

        # Check LLM detection first
        if self.llm_summary:
            llm_type = self.llm_summary.get("summary", {}).get("type", "")
            if llm_type in valid_types:
                return llm_type

        # Infer from labels
        if self.labels:
            labels_lower = [label.lower() for label in self.labels]
            for pr_type in valid_types:
                if pr_type in labels_lower or pr_type.replace("fix", "") in labels_lower:
                    return pr_type
            # Common label patterns
            if "bug" in labels_lower or "fix" in labels_lower:
                return "bugfix"
            if "enhancement" in labels_lower or "feat" in labels_lower:
                return "feature"
            if "documentation" in labels_lower:
                return "docs"

        return "unknown"
