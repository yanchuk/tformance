from django.contrib import admin

from .models import (
    AIUsageDaily,
    Commit,
    JiraIssue,
    PRReview,
    PRSurvey,
    PRSurveyReview,
    PullRequest,
    TeamMember,
    WeeklyMetrics,
)


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    """Admin for TeamMember - team members with integration identities."""

    list_display = ["display_name", "email", "team", "role", "github_username", "is_active", "created_at"]
    list_filter = ["team", "role", "is_active"]
    search_fields = ["display_name", "email", "github_username", "github_id", "jira_account_id", "slack_user_id"]
    ordering = ["team", "display_name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("team", "display_name", "email", "role", "is_active")}),
        ("Integration IDs", {"fields": ("github_username", "github_id", "jira_account_id", "slack_user_id")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


class PRReviewInline(admin.TabularInline):
    """Inline for PRReviews on PullRequest."""

    model = PRReview
    extra = 0
    readonly_fields = ["reviewer", "state", "submitted_at"]
    can_delete = False


class CommitInline(admin.TabularInline):
    """Inline for Commits on PullRequest."""

    model = Commit
    extra = 0
    readonly_fields = ["github_sha", "author", "message", "additions", "deletions", "committed_at"]
    can_delete = False
    max_num = 10


@admin.register(PullRequest)
class PullRequestAdmin(admin.ModelAdmin):
    """Admin for PullRequest - GitHub PRs with metrics."""

    list_display = [
        "github_pr_id",
        "github_repo",
        "title_truncated",
        "author",
        "state",
        "cycle_time_hours",
        "merged_at",
        "team",
    ]
    list_filter = ["team", "state", "is_revert", "is_hotfix", "github_repo"]
    search_fields = ["title", "github_repo", "author__display_name"]
    ordering = ["-pr_created_at"]
    readonly_fields = ["synced_at", "created_at", "updated_at"]
    raw_id_fields = ["author"]
    inlines = [PRReviewInline, CommitInline]

    fieldsets = (
        (None, {"fields": ("team", "github_pr_id", "github_repo", "title", "author", "state")}),
        ("Timestamps", {"fields": ("pr_created_at", "merged_at", "first_review_at")}),
        ("Metrics", {"fields": ("cycle_time_hours", "review_time_hours", "additions", "deletions")}),
        ("Flags", {"fields": ("is_revert", "is_hotfix")}),
        ("Sync", {"fields": ("synced_at", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Title")
    def title_truncated(self, obj):
        return obj.title[:50] + "..." if obj.title and len(obj.title) > 50 else obj.title


@admin.register(PRReview)
class PRReviewAdmin(admin.ModelAdmin):
    """Admin for PRReview - GitHub PR reviews."""

    list_display = ["pull_request", "reviewer", "state", "submitted_at", "team"]
    list_filter = ["team", "state"]
    search_fields = ["pull_request__title", "reviewer__display_name"]
    ordering = ["-submitted_at"]
    raw_id_fields = ["pull_request", "reviewer"]


@admin.register(Commit)
class CommitAdmin(admin.ModelAdmin):
    """Admin for Commit - GitHub commits."""

    list_display = ["sha_short", "github_repo", "author", "message_truncated", "additions", "deletions", "committed_at"]
    list_filter = ["team", "github_repo"]
    search_fields = ["github_sha", "message", "author__display_name"]
    ordering = ["-committed_at"]
    raw_id_fields = ["author", "pull_request"]

    @admin.display(description="SHA")
    def sha_short(self, obj):
        return obj.github_sha[:7]

    @admin.display(description="Message")
    def message_truncated(self, obj):
        return obj.message[:50] + "..." if obj.message and len(obj.message) > 50 else obj.message


@admin.register(JiraIssue)
class JiraIssueAdmin(admin.ModelAdmin):
    """Admin for JiraIssue - Jira issues with sprint tracking."""

    list_display = [
        "jira_key",
        "summary_truncated",
        "issue_type",
        "status",
        "assignee",
        "story_points",
        "sprint_name",
        "team",
    ]
    list_filter = ["team", "issue_type", "status", "sprint_name"]
    search_fields = ["jira_key", "jira_id", "summary", "assignee__display_name"]
    ordering = ["-issue_created_at"]
    readonly_fields = ["synced_at", "created_at", "updated_at"]
    raw_id_fields = ["assignee"]

    @admin.display(description="Summary")
    def summary_truncated(self, obj):
        return obj.summary[:50] + "..." if obj.summary and len(obj.summary) > 50 else obj.summary


@admin.register(AIUsageDaily)
class AIUsageDailyAdmin(admin.ModelAdmin):
    """Admin for AIUsageDaily - daily AI tool usage metrics."""

    list_display = [
        "member",
        "date",
        "source",
        "suggestions_shown",
        "suggestions_accepted",
        "acceptance_rate",
        "active_hours",
        "team",
    ]
    list_filter = ["team", "source", "date"]
    search_fields = ["member__display_name"]
    ordering = ["-date", "member"]
    raw_id_fields = ["member"]
    date_hierarchy = "date"


class PRSurveyReviewInline(admin.TabularInline):
    """Inline for PRSurveyReviews on PRSurvey."""

    model = PRSurveyReview
    extra = 0
    readonly_fields = ["reviewer", "quality_rating", "ai_guess", "guess_correct", "responded_at"]
    can_delete = False


@admin.register(PRSurvey)
class PRSurveyAdmin(admin.ModelAdmin):
    """Admin for PRSurvey - PR survey tracking author AI disclosure."""

    list_display = ["pull_request", "author", "author_ai_assisted", "author_responded_at", "reviews_count", "team"]
    list_filter = ["team", "author_ai_assisted"]
    search_fields = ["pull_request__title", "author__display_name"]
    ordering = ["-created_at"]
    raw_id_fields = ["pull_request", "author"]
    inlines = [PRSurveyReviewInline]

    @admin.display(description="Reviews")
    def reviews_count(self, obj):
        return obj.reviews.count()


@admin.register(PRSurveyReview)
class PRSurveyReviewAdmin(admin.ModelAdmin):
    """Admin for PRSurveyReview - reviewer responses to surveys."""

    list_display = ["survey", "reviewer", "quality_rating", "ai_guess", "guess_correct", "responded_at", "team"]
    list_filter = ["team", "quality_rating", "ai_guess", "guess_correct"]
    search_fields = ["survey__pull_request__title", "reviewer__display_name"]
    ordering = ["-responded_at"]
    raw_id_fields = ["survey", "reviewer"]


@admin.register(WeeklyMetrics)
class WeeklyMetricsAdmin(admin.ModelAdmin):
    """Admin for WeeklyMetrics - pre-computed weekly aggregates."""

    list_display = [
        "member",
        "week_start",
        "prs_merged",
        "commits_count",
        "story_points_completed",
        "ai_assisted_prs",
        "avg_quality_rating",
        "team",
    ]
    list_filter = ["team", "week_start"]
    search_fields = ["member__display_name"]
    ordering = ["-week_start", "member"]
    raw_id_fields = ["member"]
    date_hierarchy = "week_start"

    fieldsets = (
        (None, {"fields": ("team", "member", "week_start")}),
        (
            "Delivery Metrics",
            {
                "fields": (
                    "prs_merged",
                    "avg_cycle_time_hours",
                    "avg_review_time_hours",
                    "commits_count",
                    "lines_added",
                    "lines_removed",
                )
            },
        ),
        ("Quality Metrics", {"fields": ("revert_count", "hotfix_count")}),
        ("Jira Metrics", {"fields": ("story_points_completed", "issues_resolved")}),
        ("AI Metrics", {"fields": ("ai_assisted_prs",)}),
        ("Survey Metrics", {"fields": ("avg_quality_rating", "surveys_completed", "guess_accuracy")}),
    )
