from django.contrib import admin

from .models import (
    PublicOrgProfile,
    PublicOrgStats,
    PublicRepoInsight,
    PublicRepoProfile,
    PublicRepoRequest,
    PublicRepoStats,
)


@admin.register(PublicOrgProfile)
class PublicOrgProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "public_slug", "industry", "is_public")
    list_filter = ("is_public", "industry")
    search_fields = ("display_name", "public_slug")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PublicOrgStats)
class PublicOrgStatsAdmin(admin.ModelAdmin):
    list_display = (
        "org_profile",
        "total_prs",
        "ai_assisted_pct",
        "median_cycle_time_hours",
        "active_contributors_90d",
        "last_computed_at",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(PublicRepoProfile)
class PublicRepoProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "repo_slug", "org_profile", "is_flagship", "is_public")
    list_filter = ("is_flagship", "is_public")
    search_fields = ("display_name", "repo_slug", "github_repo")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PublicRepoStats)
class PublicRepoStatsAdmin(admin.ModelAdmin):
    list_display = ("repo_profile", "total_prs", "ai_assisted_pct", "median_cycle_time_hours", "last_computed_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PublicRepoInsight)
class PublicRepoInsightAdmin(admin.ModelAdmin):
    list_display = ("repo_profile", "insight_type", "is_current", "generated_at")
    list_filter = ("is_current", "insight_type")
    readonly_fields = ("created_at", "updated_at", "generated_at")


@admin.register(PublicRepoRequest)
class PublicRepoRequestAdmin(admin.ModelAdmin):
    list_display = ("github_url", "email", "role", "status", "created_at")
    list_filter = ("status", "role")
    search_fields = ("github_url", "email")
    readonly_fields = ("created_at", "updated_at")
