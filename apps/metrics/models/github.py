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
        ("javascript", "JavaScript/TypeScript"),  # Ambiguous - could be frontend or backend
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

    # File extension mappings for categorization
    # Coverage based on Stack Overflow 2025 Developer Survey
    FRONTEND_EXTENSIONS = (
        # JavaScript/TypeScript (when in frontend paths)
        ".jsx",
        ".tsx",
        # Vue, Svelte, Angular
        ".vue",
        ".svelte",
        ".angular",
        # Dart/Flutter (5.9% usage) - mobile/web frontend
        ".dart",
        # Astro (~2% usage) - static site generator
        ".astro",
        # Blazor/Razor (~2% usage) - C# frontend
        ".razor",
        # MDX - React components in Markdown
        ".mdx",
        # Styles
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".styl",
        ".stylus",
        # Templates
        ".html",
        ".htm",
        ".ejs",
        ".hbs",
        ".handlebars",
        ".pug",
        ".jade",
    )

    BACKEND_EXTENSIONS = (
        # Python
        ".py",
        ".pyw",
        ".pyx",
        # PHP
        ".php",
        ".phtml",
        ".php3",
        ".php4",
        ".php5",
        ".phps",
        # Ruby
        ".rb",
        ".erb",
        ".rake",
        # Java/JVM
        ".java",
        ".kt",
        ".kts",
        ".scala",
        ".groovy",
        ".clj",
        ".cljs",
        # .NET
        ".cs",
        ".fs",
        ".fsi",  # F# signature files
        ".vb",
        # Go
        ".go",
        # Rust
        ".rs",
        # C/C++
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cc",
        ".hh",
        ".cxx",
        ".hxx",
        # Node.js/Server JS (when not in frontend paths)
        ".mjs",
        ".cjs",
        # Elixir/Erlang
        ".ex",
        ".exs",
        ".erl",
        ".hrl",
        # Swift/Objective-C
        ".swift",
        ".m",  # Note: Also MATLAB, but context determines
        ".mm",
        # Perl
        ".pl",
        ".pm",
        # Lua
        ".lua",
        # R
        ".r",
        ".R",
        # Shell/Scripts
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        # SQL
        ".sql",
        # ======================================================================
        # Additional languages from SO 2025 Survey
        # ======================================================================
        # Assembly (7.1% usage) - systems programming
        ".asm",
        ".s",
        ".S",  # GNU assembler (case matters on Unix)
        # VBA (4.2% usage) - Office macros/automation
        ".vba",
        ".bas",  # Visual Basic module
        # Zig (2.1% usage) - systems programming
        ".zig",
        # Delphi/Pascal (2.5% usage)
        ".pas",
        ".dpr",  # Delphi project file
        ".dpk",  # Delphi package
        # Lisp (2.4% usage)
        ".lisp",
        ".cl",  # Common Lisp
        ".lsp",  # Alternative extension
        # Fortran (1.4% usage) - scientific computing
        ".f",
        ".f90",
        ".f95",
        ".f03",
        ".f08",
        ".for",
        # Ada (1.4% usage)
        ".ada",
        ".adb",  # Ada body
        ".ads",  # Ada spec
        # OCaml (1.2% usage)
        ".ml",
        ".mli",  # OCaml interface
        # Gleam (1.1% usage) - BEAM VM
        ".gleam",
        # Haskell
        ".hs",
        ".lhs",  # Literate Haskell
        # Nim
        ".nim",
        # Crystal
        ".cr",
        # Julia
        ".jl",
        # D language
        ".d",
        # V language
        ".v",
        # Zig
        ".zig",
        # Cobol (still used in enterprise)
        ".cob",
        ".cbl",
    )

    CONFIG_EXTENSIONS = (
        # Data formats
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".xml",
        # Environment/Config
        ".env",
        ".conf",
        ".cfg",
        ".config",
        ".properties",
        # Lock files
        ".lock",
        # Docker
        ".dockerfile",
        # Misc config
        ".editorconfig",
        ".prettierrc",
        ".eslintrc",
        ".babelrc",
    )

    DOCS_EXTENSIONS = (
        ".md",
        ".markdown",
        ".rst",
        ".txt",
        ".adoc",
        ".asciidoc",
        ".wiki",
        ".rdoc",
        ".org",
        ".tex",
    )

    # ==========================================================================
    # Path-based JS/TS Categorization (Tiered Priority System)
    # ==========================================================================
    # Uses full file path from GitHub API to determine frontend vs backend.
    # More specific patterns are checked first (TIER 1) before generic ones.
    # Future: Allow per-repo custom path configuration.

    # TIER 1: Backend exceptions within frontend directories (check FIRST)
    # These override frontend patterns when matched
    BACKEND_EXCEPTION_PATTERNS = (
        "/pages/api/",  # Next.js Pages Router API routes
        "/app/api/",  # Next.js App Router API routes
        "/src/pages/api/",  # Next.js in src/
        "/src/app/api/",  # Next.js in src/
    )

    # TIER 2: Unambiguous frontend patterns (high confidence)
    FRONTEND_PATH_PATTERNS = (
        # React/Vue/Angular component directories
        "/components/",
        "/hooks/",
        "/contexts/",
        "/composables/",  # Vue 3 composables
        # State management
        "/store/",
        "/stores/",
        "/redux/",
        "/pinia/",
        "/vuex/",
        # UI structure
        "/pages/",  # General pages (but /pages/api/ is excluded above)
        "/views/",
        "/layouts/",
        "/screens/",  # React Native
        "/templates/",
        # Angular-specific patterns (SO 2025: ~11% usage)
        # Note: These patterns are more specific to avoid conflicts with NestJS
        "/app/guards/",  # Angular route guards
        "/app/pipes/",  # Angular pipes
        "/app/directives/",  # Angular custom directives
        # Explicit frontend directories
        "/frontend/",
        "/client/",
        "/web/",
        "/ui/",
        # Monorepo frontend apps
        "/apps/web/",
        "/apps/dashboard/",
        "/apps/admin/",
        "/packages/ui/",
        "/packages/web/",
        "/packages/frontend/",
    )

    # TIER 3: Unambiguous backend patterns (high confidence)
    BACKEND_PATH_PATTERNS = (
        # API layer
        "/api/",
        "/apis/",
        "/endpoints/",
        "/routes/",  # Express/Fastify routes
        "/routers/",
        # Service layer
        "/controllers/",
        "/services/",
        "/handlers/",
        "/resolvers/",  # GraphQL
        # Middleware
        "/middleware/",
        "/middlewares/",
        # Data layer
        "/models/",
        "/repositories/",
        "/database/",
        "/db/",
        "/migrations/",
        "/seeds/",
        "/prisma/",
        # NestJS-specific patterns (SO 2025: ~6% usage)
        "/modules/",  # NestJS modules
        "/guards/",  # NestJS guards (Angular guards use /app/guards/ above)
        "/interceptors/",  # NestJS interceptors
        "/decorators/",  # NestJS custom decorators
        # FastAPI-specific patterns (SO 2025: ~15% usage, +5pp growth)
        "/schemas/",  # Pydantic schemas
        "/crud/",  # CRUD operations
        "/dependencies/",  # FastAPI dependencies
        "/deps/",  # FastAPI deps (short form)
        # Django-specific patterns (SO 2025: ~12% usage)
        "/forms/",  # Django forms
        "/serializers/",  # DRF serializers
        "/management/",  # Django management commands
        # Spring Boot-specific patterns (SO 2025: ~9% usage)
        "/controller/",  # Spring controllers (singular)
        "/repository/",  # Spring Data (singular)
        "/entity/",  # JPA entities
        # ASP.NET-specific patterns (SO 2025: ~14% usage)
        "/Controllers/",  # PascalCase for .NET
        "/ViewModels/",  # MVC ViewModels
        "/Data/",  # EF Core
        # Laravel-specific patterns (SO 2025: ~7% usage)
        "/app/Http/",  # Laravel HTTP layer
        "/app/Models/",  # Eloquent models
        "/app/Jobs/",  # Queue jobs
        "/database/factories/",  # Laravel factories
        # Phoenix/Elixir-specific patterns (SO 2025: ~3% usage)
        "/lib/web/",  # Phoenix web
        "/live/",  # Phoenix LiveView
        "/channels/",  # Phoenix channels
        "/plugs/",  # Elixir plugs
        # Rails-specific patterns (SO 2025: ~3% usage)
        "/app/controllers/",  # Rails controllers
        "/app/models/",  # Rails models
        "/app/jobs/",  # ActiveJob
        "/app/mailers/",  # ActionMailer
        # Explicit backend directories
        "/backend/",
        "/server/",
        # Monorepo backend apps
        "/apps/api/",
        "/apps/server/",
        "/apps/backend/",
        "/packages/api/",
        "/packages/server/",
        "/packages/backend/",
        # Build/tooling (typically backend context)
        "/scripts/",
        "/bin/",
        "/cmd/",  # Go convention
    )

    # Common config filenames (without extensions)
    CONFIG_FILENAMES = (
        "dockerfile",
        "makefile",
        "gemfile",
        "rakefile",
        "procfile",
        "vagrantfile",
        "brewfile",
        "jenkinsfile",
        "cakefile",
        ".gitignore",
        ".dockerignore",
        ".npmrc",
        ".nvmrc",
        ".ruby-version",
        ".python-version",
        ".node-version",
        ".tool-versions",
    )

    @staticmethod
    def categorize_file(filename: str) -> str:
        """Categorize file based on extension and path.

        Uses a tiered priority system:
        1. Test files (highest priority - any extension)
        2. Backend exceptions (e.g., /pages/api/ in Next.js)
        3. Unambiguous frontend patterns (/components/, /hooks/, etc.)
        4. Unambiguous backend patterns (/controllers/, /services/, etc.)
        5. Fallback to "javascript" for ambiguous JS/TS files

        Args:
            filename: Full file path from GitHub API (e.g., "src/api/users.ts")

        Returns:
            Category string: frontend, backend, javascript, test, docs, config, or other
        """
        filename_lower = filename.lower()
        # Get the base filename for test detection
        base_name = filename_lower.split("/")[-1]

        # TIER 0: Test files (highest priority - check first)
        # Check for test patterns, but avoid false positives like "latest.f08" or "spec.ads"
        # We check for:
        # - Files starting with "test" or "test_" (e.g., test_utils.py, tests.py)
        # - Files containing "_test." or "_test_" (e.g., app_test.py, app_test_helper.py)
        # - Files containing ".test." or ".spec." (e.g., app.test.js, button.spec.tsx)
        # - Files ending with "_test" before extension (e.g., utils_test.go)
        # - Directories containing "test" or "tests" or "__tests__"
        is_test_file = (
            # Directory patterns
            "/tests/" in filename_lower
            or "/test/" in filename_lower
            or "/__tests__/" in filename_lower
            # File prefix patterns
            or base_name.startswith("test_")
            or base_name.startswith("test.")
            or base_name == "tests.py"
            # File suffix patterns (before extension)
            or "_test." in base_name
            or ".test." in base_name
            or ".spec." in base_name
            or "_spec." in base_name
            # Go convention: file_test.go
            or base_name.endswith("_test.go")
            or base_name.endswith("_test.py")
            or base_name.endswith("_test.rb")
            or base_name.endswith("_test.rs")
            or base_name.endswith("_test.ts")
            or base_name.endswith("_test.js")
        )
        if is_test_file:
            return "test"

        # JavaScript/TypeScript - use tiered path pattern system
        if filename_lower.endswith((".js", ".ts", ".mjs", ".cjs")):
            # Normalize path for matching (ensure leading slash)
            path = "/" + filename_lower.lstrip("/")

            # TIER 1: Backend exceptions (check FIRST - most specific)
            # These are backend routes inside typically frontend directories
            for pattern in PRFile.BACKEND_EXCEPTION_PATTERNS:
                if pattern in path:
                    return "backend"

            # TIER 2: Unambiguous frontend patterns
            for pattern in PRFile.FRONTEND_PATH_PATTERNS:
                if pattern in path:
                    return "frontend"

            # TIER 3: Unambiguous backend patterns
            for pattern in PRFile.BACKEND_PATH_PATTERNS:
                if pattern in path:
                    return "backend"

            # TIER 4: Fallback - path doesn't match known patterns
            return "javascript"

        # Frontend (unambiguous: JSX/TSX, styles, templates)
        if filename_lower.endswith(PRFile.FRONTEND_EXTENSIONS):
            return "frontend"

        # Backend (unambiguous server-side languages)
        if filename_lower.endswith(PRFile.BACKEND_EXTENSIONS):
            return "backend"

        # Documentation
        if filename_lower.endswith(PRFile.DOCS_EXTENSIONS):
            return "docs"

        # Configuration - check extensions
        if filename_lower.endswith(PRFile.CONFIG_EXTENSIONS):
            return "config"

        # Configuration - check common filenames without extensions
        # Note: base_name was computed at the start of the function
        if base_name in PRFile.CONFIG_FILENAMES or base_name.startswith("."):
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
