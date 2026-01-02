"""
Models for the AI feedback app.
"""

from django.conf import settings
from django.db import models

from apps.teams.models import BaseTeamModel

# Content type choices for LLM feedback
CONTENT_TYPE_CHOICES = [
    ("engineering_insight", "Engineering Insight"),
    ("pr_summary", "PR Summary"),
    ("qa_answer", "Q&A Answer"),
    ("ai_detection", "AI Detection"),
]

# Category choices for feedback
CATEGORY_CHOICES = [
    ("wrong_code", "Generated wrong code"),
    ("missed_context", "Missed project context"),
    ("style_issue", "Style/formatting issue"),
    ("missing_tests", "Forgot tests"),
    ("security", "Security concern"),
    ("performance", "Performance issue"),
    ("other", "Other"),
]

# Status choices for feedback
STATUS_CHOICES = [
    ("open", "Open"),
    ("acknowledged", "Acknowledged"),
    ("resolved", "Resolved"),
]


class AIFeedback(BaseTeamModel):
    """
    Feedback about AI-generated code issues.

    Captures what went wrong when AI coding assistants generate problematic code,
    helping teams improve their AI agent configuration and rules.
    """

    # What was the issue?
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        verbose_name="Category",
        help_text="Type of issue encountered with AI-generated code",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Detailed description of what went wrong",
    )

    # Where did it happen?
    pull_request = models.ForeignKey(
        "metrics.PullRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_feedback",
        verbose_name="Pull Request",
        help_text="Associated pull request (if any)",
    )
    file_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="File path",
        help_text="Path to the file with the issue",
    )
    language = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Language",
        help_text="Programming language of the problematic code",
    )

    # Who reported it?
    reported_by = models.ForeignKey(
        "metrics.TeamMember",
        on_delete=models.SET_NULL,
        null=True,
        related_name="reported_feedback",
        verbose_name="Reported by",
        help_text="Team member who reported the issue",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
        verbose_name="Status",
        help_text="Current status of the feedback",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Resolved at",
        help_text="When the feedback was resolved",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "AI Feedback"
        verbose_name_plural = "AI Feedback"

    def __str__(self):
        return f"{self.get_category_display()} - {self.get_status_display()}"


class LLMFeedback(BaseTeamModel):
    """
    Feedback about LLM-generated content (summaries, insights, AI detection).

    Captures thumbs up/down feedback with optional comments to help improve
    LLM prompt quality and accuracy.
    """

    # What type of content is this feedback about?
    content_type = models.CharField(
        max_length=50,
        choices=CONTENT_TYPE_CHOICES,
        verbose_name="Content Type",
        help_text="Type of LLM-generated content being rated",
    )
    content_id = models.CharField(
        max_length=255,
        default="",
        verbose_name="Content ID",
        help_text="ID of the content being rated",
    )

    # Rating: True = thumbs up, False = thumbs down
    rating = models.BooleanField(
        verbose_name="Rating",
        help_text="Thumbs up (True) or thumbs down (False)",
    )

    # Optional text feedback
    comment = models.TextField(
        blank=True,
        default="",
        verbose_name="Comment",
        help_text="Optional detailed feedback about the content",
    )

    # Snapshot of the content that was rated (for audit/debugging)
    content_snapshot = models.JSONField(
        verbose_name="Content Snapshot",
        help_text="JSON snapshot of the LLM-generated content that was rated",
    )

    # Optional snapshot of the input context used to generate the content
    input_context = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Input Context",
        help_text="JSON snapshot of the input context used to generate the content",
    )

    # Version of the prompt that generated the content
    prompt_version = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="Prompt Version",
        help_text="Version of the prompt template used",
    )

    # Relations
    pull_request = models.ForeignKey(
        "metrics.PullRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_feedback",
        verbose_name="Pull Request",
        help_text="Associated pull request (if any)",
    )

    daily_insight = models.ForeignKey(
        "metrics.DailyInsight",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_feedback",
        verbose_name="Daily Insight",
        help_text="Associated daily insight (if any)",
    )

    submitted_by = models.ForeignKey(
        "metrics.TeamMember",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_llm_feedback",
        verbose_name="Submitted By",
        help_text="Team member who submitted the feedback",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="llm_feedback",
        verbose_name="User",
        help_text="User who submitted the feedback",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "LLM Feedback"
        verbose_name_plural = "LLM Feedback"
        indexes = [
            # Filter feedback by content type (e.g., all PR summary feedback)
            models.Index(fields=["content_type"], name="llm_fb_content_type_idx"),
            # Filter by rating for quality analysis (positive vs negative feedback)
            models.Index(fields=["rating"], name="llm_fb_rating_idx"),
            # Team dashboard queries - filter by team and sort by date
            models.Index(fields=["team", "created_at"], name="llm_fb_team_created_idx"),
            # Composite index for content type analysis per team
            models.Index(fields=["team", "content_type", "rating"], name="llm_fb_team_type_rate_idx"),
        ]
        constraints = [
            # Each user can only submit one feedback per content item per team
            models.UniqueConstraint(
                fields=["team", "user", "content_type", "content_id"],
                name="llm_fb_unique_user_content",
            ),
        ]

    def __str__(self):
        rating_str = "thumbs up" if self.rating else "thumbs down"
        return f"{self.get_content_type_display()} - {rating_str}"
