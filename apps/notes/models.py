"""
Models for the Personal PR Notes feature.

Allows CTOs to add private notes to PRs for later review and synthesis.
"""

from django.conf import settings
from django.db import models

from apps.utils.models import BaseModel

FLAG_CHOICES = [
    ("", "No Flag"),
    ("false_positive", "False Positive"),
    ("review_later", "Review Later"),
    ("important", "Important"),
    ("concern", "Concern"),
]


class PRNote(BaseModel):
    """
    A personal note attached to a Pull Request.

    Notes are user-scoped (only visible to the creator) and allow
    CTOs to capture observations during weekly reviews for monthly synthesis.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pr_notes",
        help_text="The user who created this note",
    )
    pull_request = models.ForeignKey(
        "metrics.PullRequest",
        on_delete=models.CASCADE,
        related_name="user_notes",
        help_text="The PR this note is attached to",
    )
    content = models.TextField(
        max_length=2000,
        help_text="The note content (max 2000 characters)",
    )
    flag = models.CharField(
        max_length=20,
        choices=FLAG_CHOICES,
        blank=True,
        default="",
        help_text="Optional category flag for filtering",
    )
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether the note has been marked as resolved",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the note was marked as resolved",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "pull_request"],
                name="unique_user_pr_note",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_resolved", "-created_at"]),
            models.Index(fields=["user", "flag"]),
        ]

    def __str__(self):
        pr_id = self.pull_request.github_pr_id
        flag_str = f" [{self.flag}]" if self.flag else ""
        return f"Note on PR #{pr_id}{flag_str}"
