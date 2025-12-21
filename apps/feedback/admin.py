"""
Admin interface for the AI Feedback app.
"""

from django.contrib import admin

from apps.feedback.models import AIFeedback


@admin.register(AIFeedback)
class AIFeedbackAdmin(admin.ModelAdmin):
    """Admin interface for AI Feedback."""

    list_display = [
        "id",
        "category",
        "status",
        "reported_by",
        "team",
        "created_at",
        "resolved_at",
    ]
    list_filter = [
        "category",
        "status",
        "team",
        "created_at",
    ]
    search_fields = [
        "description",
        "file_path",
        "reported_by__display_name",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]
    raw_id_fields = [
        "team",
        "pull_request",
        "reported_by",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
