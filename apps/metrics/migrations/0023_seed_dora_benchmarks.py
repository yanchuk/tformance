"""Seed DORA 2024 industry benchmark data."""

from django.db import migrations


def seed_benchmarks(apps, schema_editor):
    """Seed industry benchmarks based on DORA 2024 research.

    Data sources:
    - DORA State of DevOps Report 2024
    - Internal research on engineering metrics

    Note: Benchmarks vary by team size as larger teams typically have
    different baseline metrics due to coordination overhead.
    """
    IndustryBenchmark = apps.get_model("metrics", "IndustryBenchmark")

    # Benchmark data: (metric_name, team_size, p25, p50, p75, p90)
    benchmarks = [
        # Cycle Time (hours) - time from first commit to merge
        # Smaller teams tend to have faster cycle times
        ("cycle_time", "small", 24, 48, 72, 120),
        ("cycle_time", "medium", 36, 72, 120, 168),
        ("cycle_time", "large", 48, 96, 168, 240),
        ("cycle_time", "enterprise", 72, 120, 216, 336),

        # Review Time (hours) - time from PR open to first review
        ("review_time", "small", 2, 4, 8, 16),
        ("review_time", "medium", 4, 8, 16, 24),
        ("review_time", "large", 6, 12, 24, 36),
        ("review_time", "enterprise", 8, 16, 32, 48),

        # PR Count (per developer per week)
        ("pr_count", "small", 3, 5, 8, 12),
        ("pr_count", "medium", 2, 4, 7, 10),
        ("pr_count", "large", 2, 3, 5, 8),
        ("pr_count", "enterprise", 1, 3, 5, 7),

        # AI Adoption (% of PRs with AI assistance)
        # Note: This is emerging data, benchmarks will evolve
        ("ai_adoption", "small", 15, 30, 50, 70),
        ("ai_adoption", "medium", 12, 25, 45, 65),
        ("ai_adoption", "large", 10, 22, 40, 60),
        ("ai_adoption", "enterprise", 8, 20, 38, 55),

        # Deployment Frequency (per week)
        ("deployment_freq", "small", 5, 10, 20, 35),
        ("deployment_freq", "medium", 3, 7, 14, 25),
        ("deployment_freq", "large", 2, 5, 10, 18),
        ("deployment_freq", "enterprise", 1, 3, 7, 14),
    ]

    for metric, size, p25, p50, p75, p90 in benchmarks:
        IndustryBenchmark.objects.create(
            metric_name=metric,
            team_size_bucket=size,
            p25=p25,
            p50=p50,
            p75=p75,
            p90=p90,
            source="DORA State of DevOps 2024 + Internal Research",
            year=2024,
        )


def remove_benchmarks(apps, schema_editor):
    """Remove seeded benchmarks."""
    IndustryBenchmark = apps.get_model("metrics", "IndustryBenchmark")
    IndustryBenchmark.objects.filter(year=2024).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("metrics", "0022_add_industry_benchmark"),
    ]

    operations = [
        migrations.RunPython(seed_benchmarks, remove_benchmarks),
    ]
