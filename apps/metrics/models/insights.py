"""Insight models: DailyInsight."""

from django.db import models

from apps.teams.models import BaseTeamModel


class DailyInsight(BaseTeamModel):
    """
    Daily generated insights about team metrics.

    Tracks trends, anomalies, comparisons, and recommended actions based on team data.
    """

    CATEGORY_CHOICES = [
        ("trend", "Trend"),
        ("anomaly", "Anomaly"),
        ("comparison", "Comparison"),
        ("action", "Action"),
    ]

    PRIORITY_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    date = models.DateField(
        db_index=True,
        verbose_name="Date",
        help_text="Date this insight was generated for",
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name="Category",
        help_text="Type of insight (trend, anomaly, comparison, action)",
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        verbose_name="Priority",
        help_text="Priority level of this insight",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Brief title of the insight",
    )
    description = models.TextField(
        verbose_name="Description",
        help_text="Detailed description of the insight",
    )
    metric_type = models.CharField(
        max_length=100,
        verbose_name="Metric Type",
        help_text="Type of metric this insight is about (e.g., cycle_time, review_time)",
    )
    metric_value = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Metric Value",
        help_text="JSON data containing metric values and context",
    )
    comparison_period = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Comparison Period",
        help_text="Time period for comparison (e.g., week_over_week, month_over_month)",
    )
    is_dismissed = models.BooleanField(
        default=False,
        verbose_name="Is Dismissed",
        help_text="Whether this insight has been dismissed by the user",
    )
    dismissed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dismissed At",
        help_text="When this insight was dismissed",
    )

    class Meta:
        ordering = ["-date", "priority", "category"]
        verbose_name = "Daily Insight"
        verbose_name_plural = "Daily Insights"
        indexes = [
            models.Index(fields=["date", "category"], name="insight_date_cat_idx"),
            models.Index(fields=["priority", "is_dismissed"], name="insight_pri_dismissed_idx"),
        ]

    def __str__(self):
        return f"{self.date} - {self.title}"
