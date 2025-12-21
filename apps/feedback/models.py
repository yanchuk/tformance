"""
Models for the AI feedback app.
"""

from django.db import models

from apps.teams.models import BaseTeamModel

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
