from django.contrib import admin

from .models import (
    GitHubIntegration,
    IntegrationCredential,
    JiraIntegration,
    SlackIntegration,
    TrackedJiraProject,
    TrackedRepository,
)


class TrackedRepositoryInline(admin.TabularInline):
    """Inline for TrackedRepositories on GitHubIntegration."""

    model = TrackedRepository
    extra = 0
    readonly_fields = ["full_name", "github_repo_id", "is_active", "webhook_id", "last_sync_at"]
    can_delete = False
    max_num = 20


class GitHubIntegrationInline(admin.StackedInline):
    """Inline for GitHubIntegration on IntegrationCredential."""

    model = GitHubIntegration
    extra = 0
    readonly_fields = ["organization_slug", "organization_id", "sync_status", "last_sync_at"]
    can_delete = False


class JiraIntegrationInline(admin.StackedInline):
    """Inline for JiraIntegration on IntegrationCredential."""

    model = JiraIntegration
    extra = 0
    readonly_fields = ["cloud_id", "site_name", "site_url", "sync_status", "last_sync_at"]
    can_delete = False


class SlackIntegrationInline(admin.StackedInline):
    """Inline for SlackIntegration on IntegrationCredential."""

    model = SlackIntegration
    extra = 0
    readonly_fields = ["workspace_id", "workspace_name", "bot_user_id", "sync_status", "last_sync_at"]
    can_delete = False


class TrackedJiraProjectInline(admin.TabularInline):
    """Inline for TrackedJiraProjects on JiraIntegration."""

    model = TrackedJiraProject
    extra = 0
    readonly_fields = ["jira_project_key", "jira_project_id", "name", "is_active", "last_sync_at"]
    can_delete = False
    max_num = 20


@admin.register(IntegrationCredential)
class IntegrationCredentialAdmin(admin.ModelAdmin):
    """Admin for IntegrationCredential - OAuth tokens for integrations."""

    list_display = ["provider", "team", "connected_by", "token_status", "connected_at"]
    list_filter = ["team", "provider"]
    search_fields = ["team__name", "connected_by__email"]
    ordering = ["team", "provider"]
    readonly_fields = ["created_at", "updated_at", "token_masked"]
    raw_id_fields = ["connected_by"]
    inlines = [GitHubIntegrationInline, JiraIntegrationInline, SlackIntegrationInline]

    fieldsets = (
        (None, {"fields": ("team", "provider", "connected_by")}),
        ("Token Info", {"fields": ("token_masked", "token_expires_at", "scopes")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Token")
    def token_masked(self, obj):
        """Show masked token for security."""
        if obj.access_token:
            return f"{obj.access_token[:8]}...{obj.access_token[-4:]}" if len(obj.access_token) > 12 else "***"
        return "-"

    @admin.display(description="Status")
    def token_status(self, obj):
        """Show if token is expired or valid."""
        from django.utils import timezone

        if not obj.access_token:
            return "No token"
        if obj.token_expires_at and obj.token_expires_at < timezone.now():
            return "Expired"
        return "Valid"

    @admin.display(description="Connected")
    def connected_at(self, obj):
        return obj.created_at


@admin.register(GitHubIntegration)
class GitHubIntegrationAdmin(admin.ModelAdmin):
    """Admin for GitHubIntegration - GitHub organization settings."""

    list_display = [
        "organization_slug",
        "team",
        "sync_status",
        "last_sync_at",
        "repos_count",
        "active_repos_count",
    ]
    list_filter = ["team", "sync_status"]
    search_fields = ["organization_slug", "team__name"]
    ordering = ["team", "organization_slug"]
    readonly_fields = ["created_at", "updated_at", "credential"]
    inlines = [TrackedRepositoryInline]

    fieldsets = (
        (None, {"fields": ("team", "credential", "organization_slug", "organization_id")}),
        ("Sync Status", {"fields": ("sync_status", "last_sync_at")}),
        ("Security", {"fields": ("webhook_secret",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Total Repos")
    def repos_count(self, obj):
        return obj.tracked_repositories.count()

    @admin.display(description="Active Repos")
    def active_repos_count(self, obj):
        return obj.tracked_repositories.filter(is_active=True).count()


@admin.register(TrackedRepository)
class TrackedRepositoryAdmin(admin.ModelAdmin):
    """Admin for TrackedRepository - GitHub repositories being tracked."""

    list_display = [
        "full_name",
        "team",
        "integration_org",
        "is_active",
        "webhook_status",
        "last_sync_at",
    ]
    list_filter = ["team", "is_active", "integration__organization_slug"]
    search_fields = ["full_name", "team__name"]
    ordering = ["team", "full_name"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["integration"]

    fieldsets = (
        (None, {"fields": ("team", "integration", "full_name", "github_repo_id")}),
        ("Status", {"fields": ("is_active", "webhook_id", "last_sync_at")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Organization")
    def integration_org(self, obj):
        return obj.integration.organization_slug if obj.integration else "-"

    @admin.display(description="Webhook")
    def webhook_status(self, obj):
        return "Registered" if obj.webhook_id else "Not registered"


@admin.register(JiraIntegration)
class JiraIntegrationAdmin(admin.ModelAdmin):
    """Admin for JiraIntegration - Jira site settings."""

    list_display = [
        "site_name",
        "team",
        "sync_status",
        "last_sync_at",
        "cloud_id",
        "projects_count",
        "active_projects_count",
    ]
    list_filter = ["team", "sync_status"]
    search_fields = ["site_name", "team__name", "cloud_id"]
    ordering = ["team", "site_name"]
    readonly_fields = ["created_at", "updated_at", "credential"]
    inlines = [TrackedJiraProjectInline]

    fieldsets = (
        (None, {"fields": ("team", "credential", "site_name", "cloud_id", "site_url")}),
        ("Sync Status", {"fields": ("sync_status", "last_sync_at")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Total Projects")
    def projects_count(self, obj):
        return obj.tracked_jira_projects.count()

    @admin.display(description="Active Projects")
    def active_projects_count(self, obj):
        return obj.tracked_jira_projects.filter(is_active=True).count()


@admin.register(TrackedJiraProject)
class TrackedJiraProjectAdmin(admin.ModelAdmin):
    """Admin for TrackedJiraProject - Jira projects being tracked."""

    list_display = [
        "jira_project_key",
        "name",
        "team",
        "integration_site",
        "is_active",
        "sync_status",
        "last_sync_at",
    ]
    list_filter = ["team", "is_active", "sync_status", "integration__site_name"]
    search_fields = ["jira_project_key", "name", "team__name"]
    ordering = ["team", "name"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["integration"]

    fieldsets = (
        (None, {"fields": ("team", "integration", "jira_project_key", "jira_project_id", "name")}),
        ("Status", {"fields": ("is_active", "sync_status", "last_sync_at", "last_sync_error")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Site")
    def integration_site(self, obj):
        return obj.integration.site_name if obj.integration else "-"


@admin.register(SlackIntegration)
class SlackIntegrationAdmin(admin.ModelAdmin):
    """Admin for SlackIntegration - Slack workspace settings."""

    list_display = [
        "workspace_name",
        "team",
        "sync_status",
        "last_sync_at",
        "leaderboard_enabled",
        "surveys_enabled",
        "reveals_enabled",
    ]
    list_filter = ["team", "sync_status", "leaderboard_enabled", "surveys_enabled", "reveals_enabled"]
    search_fields = ["workspace_name", "team__name", "workspace_id"]
    ordering = ["team", "workspace_name"]
    readonly_fields = ["created_at", "updated_at", "credential"]

    fieldsets = (
        (None, {"fields": ("team", "credential", "workspace_name", "workspace_id", "bot_user_id")}),
        (
            "Leaderboard Settings",
            {
                "fields": (
                    "leaderboard_enabled",
                    "leaderboard_channel_id",
                    "leaderboard_day",
                    "leaderboard_time",
                )
            },
        ),
        ("Features", {"fields": ("surveys_enabled", "reveals_enabled")}),
        ("Sync Status", {"fields": ("sync_status", "last_sync_at")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
