"""Survey models: PRSurvey, PRSurveyReview."""

from django.db import models

from apps.teams.models import BaseTeamModel

from .github import PullRequest
from .team import TeamMember


class PRSurvey(BaseTeamModel):
    """Survey for a Pull Request - tracks author's AI disclosure."""

    pull_request = models.OneToOneField(
        PullRequest,
        on_delete=models.CASCADE,
        related_name="survey",
        verbose_name="Pull Request",
        help_text="The PR this survey is for",
    )
    author = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="authored_surveys",
        verbose_name="Author",
        help_text="The PR author",
    )

    # Token fields for survey access
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        verbose_name="Token",
        help_text="Unique token for accessing the survey via URL",
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Token Expires At",
        help_text="When the survey token expires (typically 7 days after creation)",
    )
    github_comment_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="GitHub Comment ID",
        help_text="The GitHub comment ID where the survey was posted",
    )

    author_ai_assisted = models.BooleanField(
        null=True,
        verbose_name="Author AI Assisted",
        help_text="Whether the author used AI tools (null = not responded yet)",
    )
    author_responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Author Responded At",
        help_text="When the author responded to the survey",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "PR Survey"
        verbose_name_plural = "PR Surveys"
        indexes = [
            models.Index(fields=["pull_request"], name="pr_survey_pr_idx"),
            models.Index(fields=["author", "author_ai_assisted"], name="pr_survey_author_ai_idx"),
            models.Index(fields=["author_responded_at"], name="pr_survey_responded_idx"),
        ]

    def __str__(self):
        return f"Survey for PR #{self.pull_request.github_pr_id}"

    def is_token_expired(self):
        """Check if the survey token has expired."""
        if self.token_expires_at is None:
            return True
        from django.utils import timezone

        return self.token_expires_at < timezone.now()

    def has_author_responded(self) -> bool:
        """Check if the author has responded to the survey.

        The author_ai_assisted field starts as None and becomes a boolean (True/False)
        once the author responds. This method checks if it's been set to a boolean value.

        Returns:
            bool: True if the author has responded, False otherwise
        """
        return isinstance(self.author_ai_assisted, bool)


class PRSurveyReview(BaseTeamModel):
    """Reviewer's response to a PR survey."""

    QUALITY_CHOICES = [
        (1, "Could be better"),
        (2, "OK"),
        (3, "Super"),
    ]

    survey = models.ForeignKey(
        PRSurvey,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Survey",
        help_text="The survey this review is for",
    )
    reviewer = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name="survey_reviews",
        verbose_name="Reviewer",
        help_text="The reviewer providing feedback",
    )

    quality_rating = models.IntegerField(
        choices=QUALITY_CHOICES,
        null=True,
        verbose_name="Quality Rating",
        help_text="Reviewer's quality rating of the PR",
    )
    ai_guess = models.BooleanField(
        null=True,
        verbose_name="AI Guess",
        help_text="Reviewer's guess whether AI was used",
    )
    guess_correct = models.BooleanField(
        null=True,
        verbose_name="Guess Correct",
        help_text="Whether the reviewer's guess was correct",
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Responded At",
        help_text="When the reviewer responded",
    )

    class Meta:
        ordering = ["-responded_at"]
        verbose_name = "PR Survey Review"
        verbose_name_plural = "PR Survey Reviews"
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "reviewer"],
                name="unique_survey_reviewer",
            )
        ]
        indexes = [
            models.Index(fields=["survey", "responded_at"], name="pr_survey_review_survey_idx"),
            models.Index(fields=["reviewer", "responded_at"], name="pr_survey_review_reviewer_idx"),
            models.Index(fields=["quality_rating"], name="pr_survey_review_quality_idx"),
        ]

    def __str__(self):
        reviewer_name = self.reviewer.display_name if self.reviewer else "Unknown"
        return f"Review by {reviewer_name} on Survey #{self.survey.pull_request.github_pr_id}"
