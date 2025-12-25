"""Industry benchmark models for comparing team metrics."""

from django.db import models

from apps.utils.models import BaseModel


class IndustryBenchmark(BaseModel):
    """Industry benchmark data for comparing team performance.

    Stores percentile data from industry reports (like DORA) to enable
    teams to compare their metrics against similar-sized organizations.

    Team size buckets:
    - small: 1-10 engineers
    - medium: 11-50 engineers
    - large: 51-200 engineers
    - enterprise: 201+ engineers
    """

    TEAM_SIZE_CHOICES = [
        ("small", "Small (1-10)"),
        ("medium", "Medium (11-50)"),
        ("large", "Large (51-200)"),
        ("enterprise", "Enterprise (201+)"),
    ]

    METRIC_CHOICES = [
        ("cycle_time", "Cycle Time (hours)"),
        ("review_time", "Review Time (hours)"),
        ("pr_count", "PRs Merged per Week"),
        ("ai_adoption", "AI Adoption %"),
        ("deployment_freq", "Deployment Frequency"),
    ]

    metric_name = models.CharField(
        max_length=50,
        choices=METRIC_CHOICES,
        help_text="The metric this benchmark applies to",
    )
    team_size_bucket = models.CharField(
        max_length=20,
        choices=TEAM_SIZE_CHOICES,
        help_text="Team size category",
    )

    # Percentile values - lower percentile = better for time metrics
    p25 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="25th percentile (elite performers)",
    )
    p50 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="50th percentile (median)",
    )
    p75 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="75th percentile",
    )
    p90 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="90th percentile (needs improvement)",
    )

    source = models.CharField(
        max_length=100,
        help_text="Data source (e.g., 'DORA 2024', 'Internal Research')",
    )
    year = models.PositiveIntegerField(
        help_text="Year the benchmark data was collected",
    )

    class Meta:
        unique_together = ["metric_name", "team_size_bucket", "year"]
        ordering = ["metric_name", "team_size_bucket"]
        verbose_name = "Industry Benchmark"
        verbose_name_plural = "Industry Benchmarks"

    def __str__(self):
        return f"{self.get_metric_name_display()} - {self.get_team_size_bucket_display()} ({self.year})"
