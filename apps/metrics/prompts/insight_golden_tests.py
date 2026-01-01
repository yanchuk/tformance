"""Golden test cases for LLM insight generation evaluation.

This module defines test scenarios for evaluating the dashboard insights LLM prompt.
Each scenario represents different team metrics states and expected insight qualities.

Usage:
    from apps.metrics.prompts.insight_golden_tests import INSIGHT_GOLDEN_TESTS

    for test in INSIGHT_GOLDEN_TESTS:
        print(f"{test.id}: {test.description}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class InsightScenario(Enum):
    """Categories of insight test scenarios."""

    VELOCITY_GOOD = "velocity_good"  # Improved velocity metrics
    VELOCITY_BAD = "velocity_bad"  # Degraded velocity metrics
    AI_POSITIVE = "ai_positive"  # AI helping the team
    AI_NEGATIVE = "ai_negative"  # AI not helping
    QUALITY_ISSUE = "quality_issue"  # Quality problems detected
    TEAM_HEALTH = "team_health"  # Team distribution/bottleneck issues
    MIXED = "mixed"  # Mixed signals requiring nuance


@dataclass
class InsightGoldenTest:
    """A single golden test case for insight generation evaluation.

    Attributes:
        id: Unique identifier (e.g., "cycle_time_regression")
        description: Human-readable description
        scenario: Test scenario category

        # Input data (matches gather_insight_data output)
        velocity: Velocity metrics dict
        quality: Quality metrics dict
        team_health: Team health metrics dict
        ai_impact: AI impact metrics dict
        metadata: Period metadata dict

        # Expectations
        expected_headline_contains: Phrases that MUST appear in headline
        expected_headline_not_contains: Phrases that must NOT appear in headline
        expected_trend: Expected overall sentiment (positive/negative/mixed)
        expected_focus_metric: Which metric should be highlighted
        notes: Test case notes
    """

    id: str
    description: str
    scenario: InsightScenario

    # Input data
    velocity: dict = field(default_factory=dict)
    quality: dict = field(default_factory=dict)
    team_health: dict = field(default_factory=dict)
    ai_impact: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    # Expectations
    expected_headline_contains: list[str] = field(default_factory=list)
    expected_headline_not_contains: list[str] = field(default_factory=list)
    expected_trend: str = ""  # positive, negative, mixed
    expected_focus_metric: str = ""  # throughput, cycle_time, ai_adoption, quality
    notes: str = ""


# Helper to create standard metadata
def _metadata(team_name: str = "Engineering", days: int = 30) -> dict:
    return {
        "start_date": "2025-11-24",
        "end_date": "2025-12-24",
        "days": days,
        "team_name": team_name,
    }


# =============================================================================
# GOLDEN TEST CASES
# =============================================================================

INSIGHT_GOLDEN_TESTS: list[InsightGoldenTest] = [
    # -------------------------------------------------------------------------
    # VELOCITY ISSUES
    # -------------------------------------------------------------------------
    InsightGoldenTest(
        id="cycle_time_regression",
        description="High throughput but severe cycle time regression",
        scenario=InsightScenario.VELOCITY_BAD,
        velocity={
            "throughput": {"current": 123, "previous": 98, "pct_change": 25.5},
            "cycle_time": {"current": Decimal("169.4"), "previous": Decimal("71.8"), "pct_change": 135.8},
            "review_time": {"current": Decimal("72.5"), "previous": Decimal("22.2"), "pct_change": 226.5},
        },
        quality={
            "revert_count": 1,
            "revert_rate": 0.8,
            "hotfix_count": 0,
            "hotfix_rate": 0.0,
            "avg_review_rounds": 0.8,
            "large_pr_pct": 17.9,
        },
        team_health={
            "active_contributors": 25,
            "pr_distribution": {"top_contributor_pct": 17.1, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 19.9, "max_reviews": 72},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 42,
            "non_ai_pr_count": 81,
            "ai_adoption_pct": 34.1,
            "ai_avg_cycle_time": Decimal("214.6"),
            "non_ai_avg_cycle_time": Decimal("145.9"),
            "cycle_time_difference_pct": Decimal("47.1"),
        },
        metadata=_metadata("Antiwork"),
        expected_headline_contains=["cycle time", "slow"],
        expected_headline_not_contains=["great", "excellent", "impressive"],
        expected_trend="negative",
        expected_focus_metric="cycle_time",
        notes="Real Antiwork data. Should highlight cycle time issue as primary concern.",
    ),
    InsightGoldenTest(
        id="throughput_drop",
        description="Significant throughput drop with stable cycle time",
        scenario=InsightScenario.VELOCITY_BAD,
        velocity={
            "throughput": {"current": 45, "previous": 78, "pct_change": -42.3},
            "cycle_time": {"current": Decimal("24.0"), "previous": Decimal("26.0"), "pct_change": -7.7},
            "review_time": {"current": Decimal("4.0"), "previous": Decimal("5.0"), "pct_change": -20.0},
        },
        quality={
            "revert_count": 0,
            "revert_rate": 0.0,
            "hotfix_count": 0,
            "hotfix_rate": 0.0,
            "avg_review_rounds": 1.2,
            "large_pr_pct": 15.0,
        },
        team_health={
            "active_contributors": 8,
            "pr_distribution": {"top_contributor_pct": 25.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 5.0, "max_reviews": 12},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 15,
            "non_ai_pr_count": 30,
            "ai_adoption_pct": 33.3,
            "ai_avg_cycle_time": Decimal("22.0"),
            "non_ai_avg_cycle_time": Decimal("25.0"),
            "cycle_time_difference_pct": Decimal("-12.0"),
        },
        metadata=_metadata(),
        expected_headline_contains=["throughput"],  # "drop" or "fell"
        expected_trend="negative",
        expected_focus_metric="throughput",
        notes="Throughput dropped significantly, should be the focus even though cycle time improved.",
    ),
    # -------------------------------------------------------------------------
    # AI IMPACT
    # -------------------------------------------------------------------------
    InsightGoldenTest(
        id="ai_helping",
        description="High AI adoption with faster cycle times",
        scenario=InsightScenario.AI_POSITIVE,
        velocity={
            "throughput": {"current": 80, "previous": 70, "pct_change": 14.3},
            "cycle_time": {"current": Decimal("18.0"), "previous": Decimal("28.0"), "pct_change": -35.7},
            "review_time": {"current": Decimal("3.0"), "previous": Decimal("6.0"), "pct_change": -50.0},
        },
        quality={
            "revert_count": 1,
            "revert_rate": 1.25,
            "hotfix_count": 0,
            "hotfix_rate": 0.0,
            "avg_review_rounds": 1.1,
            "large_pr_pct": 10.0,
        },
        team_health={
            "active_contributors": 12,
            "pr_distribution": {"top_contributor_pct": 20.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 8.0, "max_reviews": 15},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 56,
            "non_ai_pr_count": 24,
            "ai_adoption_pct": 70.0,
            "ai_avg_cycle_time": Decimal("14.0"),
            "non_ai_avg_cycle_time": Decimal("26.0"),
            "cycle_time_difference_pct": Decimal("-46.2"),
        },
        metadata=_metadata(),
        expected_headline_contains=["AI"],  # "faster" or "cutting" or "boosts"
        expected_headline_not_contains=["slower", "hurts"],
        expected_trend="positive",
        expected_focus_metric="ai_adoption",
        notes="AI-assisted PRs are significantly faster, should highlight this success.",
    ),
    InsightGoldenTest(
        id="ai_not_helping",
        description="High AI adoption but slower cycle times",
        scenario=InsightScenario.AI_NEGATIVE,
        velocity={
            "throughput": {"current": 60, "previous": 55, "pct_change": 9.1},
            "cycle_time": {"current": Decimal("40.0"), "previous": Decimal("30.0"), "pct_change": 33.3},
            "review_time": {"current": Decimal("12.0"), "previous": Decimal("8.0"), "pct_change": 50.0},
        },
        quality={
            "revert_count": 3,
            "revert_rate": 5.0,
            "hotfix_count": 1,
            "hotfix_rate": 1.7,
            "avg_review_rounds": 2.5,
            "large_pr_pct": 25.0,
        },
        team_health={
            "active_contributors": 10,
            "pr_distribution": {"top_contributor_pct": 22.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 6.0, "max_reviews": 18},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 42,
            "non_ai_pr_count": 18,
            "ai_adoption_pct": 70.0,
            "ai_avg_cycle_time": Decimal("48.0"),
            "non_ai_avg_cycle_time": Decimal("24.0"),
            "cycle_time_difference_pct": Decimal("100.0"),
        },
        metadata=_metadata(),
        expected_headline_contains=["AI", "slow"],  # "slower" or "slowing"
        expected_headline_not_contains=["great", "success", "faster"],
        expected_trend="negative",
        expected_focus_metric="ai_adoption",
        notes="AI PRs take 2x longer. Should flag this as concerning.",
    ),
    # -------------------------------------------------------------------------
    # QUALITY ISSUES
    # -------------------------------------------------------------------------
    InsightGoldenTest(
        id="high_revert_rate",
        description="High revert rate indicating quality issues",
        scenario=InsightScenario.QUALITY_ISSUE,
        velocity={
            "throughput": {"current": 100, "previous": 90, "pct_change": 11.1},
            "cycle_time": {"current": Decimal("20.0"), "previous": Decimal("22.0"), "pct_change": -9.1},
            "review_time": {"current": Decimal("4.0"), "previous": Decimal("5.0"), "pct_change": -20.0},
        },
        quality={
            "revert_count": 12,
            "revert_rate": 12.0,
            "hotfix_count": 5,
            "hotfix_rate": 5.0,
            "avg_review_rounds": 1.8,
            "large_pr_pct": 30.0,
        },
        team_health={
            "active_contributors": 15,
            "pr_distribution": {"top_contributor_pct": 18.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 7.0, "max_reviews": 20},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 40,
            "non_ai_pr_count": 60,
            "ai_adoption_pct": 40.0,
            "ai_avg_cycle_time": Decimal("19.0"),
            "non_ai_avg_cycle_time": Decimal("21.0"),
            "cycle_time_difference_pct": Decimal("-9.5"),
        },
        metadata=_metadata(),
        expected_headline_contains=["revert", "quality"],
        expected_trend="negative",
        expected_focus_metric="quality",
        notes="12% revert rate is very high, should be the main concern.",
    ),
    # -------------------------------------------------------------------------
    # TEAM HEALTH
    # -------------------------------------------------------------------------
    InsightGoldenTest(
        id="bottleneck_detected",
        description="Review bottleneck with one person overloaded",
        scenario=InsightScenario.TEAM_HEALTH,
        velocity={
            "throughput": {"current": 50, "previous": 55, "pct_change": -9.1},
            "cycle_time": {"current": Decimal("72.0"), "previous": Decimal("36.0"), "pct_change": 100.0},
            "review_time": {"current": Decimal("48.0"), "previous": Decimal("12.0"), "pct_change": 300.0},
        },
        quality={
            "revert_count": 1,
            "revert_rate": 2.0,
            "hotfix_count": 0,
            "hotfix_rate": 0.0,
            "avg_review_rounds": 1.5,
            "large_pr_pct": 18.0,
        },
        team_health={
            "active_contributors": 8,
            "pr_distribution": {"top_contributor_pct": 25.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 6.0, "max_reviews": 35},
            "bottleneck": {
                "reviewer_name": "Alice",
                "pending_count": 15,
                "team_avg": 3,
            },
        },
        ai_impact={
            "ai_pr_count": 20,
            "non_ai_pr_count": 30,
            "ai_adoption_pct": 40.0,
            "ai_avg_cycle_time": Decimal("70.0"),
            "non_ai_avg_cycle_time": Decimal("74.0"),
            "cycle_time_difference_pct": Decimal("-5.4"),
        },
        metadata=_metadata(),
        expected_headline_contains=["cycle"],  # May focus on cycle time or bottleneck
        expected_headline_not_contains=["great", "improved"],
        expected_trend="negative",
        expected_focus_metric="cycle_time",
        notes="Review time jumped 300%, Alice has 5x team average pending reviews.",
    ),
    InsightGoldenTest(
        id="bus_factor_risk",
        description="Work concentrated on one person",
        scenario=InsightScenario.TEAM_HEALTH,
        velocity={
            "throughput": {"current": 40, "previous": 35, "pct_change": 14.3},
            "cycle_time": {"current": Decimal("24.0"), "previous": Decimal("26.0"), "pct_change": -7.7},
            "review_time": {"current": Decimal("6.0"), "previous": Decimal("8.0"), "pct_change": -25.0},
        },
        quality={
            "revert_count": 0,
            "revert_rate": 0.0,
            "hotfix_count": 0,
            "hotfix_rate": 0.0,
            "avg_review_rounds": 1.0,
            "large_pr_pct": 12.0,
        },
        team_health={
            "active_contributors": 5,
            "pr_distribution": {"top_contributor_pct": 65.0, "is_concentrated": True},
            "review_distribution": {"avg_reviews_per_reviewer": 8.0, "max_reviews": 20},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 10,
            "non_ai_pr_count": 30,
            "ai_adoption_pct": 25.0,
            "ai_avg_cycle_time": Decimal("22.0"),
            "non_ai_avg_cycle_time": Decimal("25.0"),
            "cycle_time_difference_pct": Decimal("-12.0"),
        },
        metadata=_metadata(),
        expected_headline_contains=["concentration"],  # "concentrated" or "concentration"
        expected_headline_not_contains=["great", "improved"],
        expected_trend="negative",
        expected_focus_metric="team_health",
        notes="One person doing 65% of work is a bus factor risk.",
    ),
    # -------------------------------------------------------------------------
    # POSITIVE SCENARIOS
    # -------------------------------------------------------------------------
    InsightGoldenTest(
        id="all_metrics_improved",
        description="All metrics improved - celebrate success",
        scenario=InsightScenario.VELOCITY_GOOD,
        velocity={
            "throughput": {"current": 100, "previous": 80, "pct_change": 25.0},
            "cycle_time": {"current": Decimal("16.0"), "previous": Decimal("24.0"), "pct_change": -33.3},
            "review_time": {"current": Decimal("2.0"), "previous": Decimal("4.0"), "pct_change": -50.0},
        },
        quality={
            "revert_count": 1,
            "revert_rate": 1.0,
            "hotfix_count": 0,
            "hotfix_rate": 0.0,
            "avg_review_rounds": 1.0,
            "large_pr_pct": 8.0,
        },
        team_health={
            "active_contributors": 15,
            "pr_distribution": {"top_contributor_pct": 15.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 7.0, "max_reviews": 12},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 60,
            "non_ai_pr_count": 40,
            "ai_adoption_pct": 60.0,
            "ai_avg_cycle_time": Decimal("12.0"),
            "non_ai_avg_cycle_time": Decimal("22.0"),
            "cycle_time_difference_pct": Decimal("-45.5"),
        },
        metadata=_metadata(),
        expected_headline_contains=["faster"],  # AI is faster, cycle time improved
        expected_headline_not_contains=["concern", "warning", "issue", "slower", "drop"],
        expected_trend="positive",
        expected_focus_metric="throughput",
        notes="Everything is improving, should be a positive summary.",
    ),
    # -------------------------------------------------------------------------
    # NEW: STAGNATION AND MIXED SCENARIOS
    # -------------------------------------------------------------------------
    InsightGoldenTest(
        id="stagnation",
        description="Flat metrics - no progress or regression",
        scenario=InsightScenario.MIXED,
        velocity={
            "throughput": {"current": 50, "previous": 48, "pct_change": 4.2},
            "cycle_time": {"current": Decimal("36.0"), "previous": Decimal("35.0"), "pct_change": 2.9},
            "review_time": {"current": Decimal("8.0"), "previous": Decimal("7.5"), "pct_change": 6.7},
        },
        quality={
            "revert_count": 2,
            "revert_rate": 4.0,
            "hotfix_count": 1,
            "hotfix_rate": 2.0,
            "avg_review_rounds": 1.4,
            "large_pr_pct": 18.0,
        },
        team_health={
            "active_contributors": 10,
            "pr_distribution": {"top_contributor_pct": 22.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 5.0, "max_reviews": 12},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 18,
            "non_ai_pr_count": 32,
            "ai_adoption_pct": 36.0,
            "ai_avg_cycle_time": Decimal("34.0"),
            "non_ai_avg_cycle_time": Decimal("37.0"),
            "cycle_time_difference_pct": Decimal("-8.1"),
        },
        metadata=_metadata(),
        expected_headline_contains=[],  # Removed - small changes are legitimately reportable
        expected_headline_not_contains=["crisis", "major", "severe"],
        expected_trend="neutral",
        expected_focus_metric="throughput",
        notes="All metrics within ±10%. Small changes can be noted without being crises.",
    ),
    InsightGoldenTest(
        id="fast_but_low_volume",
        description="Quick cycle times but very few PRs merged",
        scenario=InsightScenario.MIXED,
        velocity={
            "throughput": {"current": 12, "previous": 15, "pct_change": -20.0},
            "cycle_time": {"current": Decimal("8.0"), "previous": Decimal("12.0"), "pct_change": -33.3},
            "review_time": {"current": Decimal("1.5"), "previous": Decimal("2.5"), "pct_change": -40.0},
        },
        quality={
            "revert_count": 0,
            "revert_rate": 0.0,
            "hotfix_count": 0,
            "hotfix_rate": 0.0,
            "avg_review_rounds": 1.0,
            "large_pr_pct": 8.0,
        },
        team_health={
            "active_contributors": 6,
            "pr_distribution": {"top_contributor_pct": 35.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 2.0, "max_reviews": 5},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 5,
            "non_ai_pr_count": 7,
            "ai_adoption_pct": 41.7,
            "ai_avg_cycle_time": Decimal("7.0"),
            "non_ai_avg_cycle_time": Decimal("9.0"),
            "cycle_time_difference_pct": Decimal("-22.2"),
        },
        metadata=_metadata(),
        expected_headline_contains=[],  # Model may focus on AI impact or throughput - both valid
        expected_headline_not_contains=["crisis", "great success", "excellent"],
        expected_trend="mixed",
        expected_focus_metric="throughput",
        notes="Team is efficient but low output. Either AI impact or low volume focus is valid.",
    ),
    InsightGoldenTest(
        id="large_pr_problem",
        description="High percentage of large PRs causing review burden",
        scenario=InsightScenario.QUALITY_ISSUE,
        velocity={
            "throughput": {"current": 65, "previous": 60, "pct_change": 8.3},
            "cycle_time": {"current": Decimal("56.0"), "previous": Decimal("32.0"), "pct_change": 75.0},
            "review_time": {"current": Decimal("24.0"), "previous": Decimal("10.0"), "pct_change": 140.0},
        },
        quality={
            "revert_count": 4,
            "revert_rate": 6.2,
            "hotfix_count": 2,
            "hotfix_rate": 3.1,
            "avg_review_rounds": 2.8,
            "large_pr_pct": 45.0,
        },
        team_health={
            "active_contributors": 12,
            "pr_distribution": {"top_contributor_pct": 20.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 6.0, "max_reviews": 15},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 25,
            "non_ai_pr_count": 40,
            "ai_adoption_pct": 38.5,
            "ai_avg_cycle_time": Decimal("52.0"),
            "non_ai_avg_cycle_time": Decimal("58.0"),
            "cycle_time_difference_pct": Decimal("-10.3"),
        },
        metadata=_metadata(),
        expected_headline_contains=["cycle"],  # Model correctly identifies cycle time impact
        expected_headline_not_contains=["excellent", "great"],
        expected_trend="negative",
        expected_focus_metric="quality",
        notes="45% large PRs cause slow reviews. Model may focus on cycle time (the symptom) - valid.",
    ),
    InsightGoldenTest(
        id="review_churn",
        description="High review rounds indicating excessive rework",
        scenario=InsightScenario.QUALITY_ISSUE,
        velocity={
            "throughput": {"current": 55, "previous": 50, "pct_change": 10.0},
            "cycle_time": {"current": Decimal("48.0"), "previous": Decimal("28.0"), "pct_change": 71.4},
            "review_time": {"current": Decimal("6.0"), "previous": Decimal("5.0"), "pct_change": 20.0},
        },
        quality={
            "revert_count": 2,
            "revert_rate": 3.6,
            "hotfix_count": 1,
            "hotfix_rate": 1.8,
            "avg_review_rounds": 3.8,
            "large_pr_pct": 20.0,
        },
        team_health={
            "active_contributors": 10,
            "pr_distribution": {"top_contributor_pct": 25.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 5.5, "max_reviews": 14},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 22,
            "non_ai_pr_count": 33,
            "ai_adoption_pct": 40.0,
            "ai_avg_cycle_time": Decimal("45.0"),
            "non_ai_avg_cycle_time": Decimal("50.0"),
            "cycle_time_difference_pct": Decimal("-10.0"),
        },
        metadata=_metadata(),
        expected_headline_contains=["cycle"],  # Model focuses on cycle time impact (valid)
        expected_headline_not_contains=["excellent", "great"],
        expected_trend="negative",
        expected_focus_metric="quality",
        notes="3.8 review rounds causes cycle time delays. Model may focus on cycle time (outcome) - valid.",
    ),
    InsightGoldenTest(
        id="mixed_velocity_quality",
        description="Fast velocity but quality suffering - speed vs quality tradeoff",
        scenario=InsightScenario.MIXED,
        velocity={
            "throughput": {"current": 95, "previous": 70, "pct_change": 35.7},
            "cycle_time": {"current": Decimal("14.0"), "previous": Decimal("22.0"), "pct_change": -36.4},
            "review_time": {"current": Decimal("2.0"), "previous": Decimal("4.0"), "pct_change": -50.0},
        },
        quality={
            "revert_count": 8,
            "revert_rate": 8.4,
            "hotfix_count": 4,
            "hotfix_rate": 4.2,
            "avg_review_rounds": 0.8,
            "large_pr_pct": 12.0,
        },
        team_health={
            "active_contributors": 14,
            "pr_distribution": {"top_contributor_pct": 18.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 7.0, "max_reviews": 15},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 50,
            "non_ai_pr_count": 45,
            "ai_adoption_pct": 52.6,
            "ai_avg_cycle_time": Decimal("12.0"),
            "non_ai_avg_cycle_time": Decimal("16.0"),
            "cycle_time_difference_pct": Decimal("-25.0"),
        },
        metadata=_metadata(),
        expected_headline_contains=["revert"],  # Quality is priority #1 in prompt
        expected_headline_not_contains=["excellent"],
        expected_trend="negative",
        expected_focus_metric="quality",
        notes="Throughput up 36% and cycle time down 36% is great, but 8.4% revert rate is a crisis.",
    ),
    InsightGoldenTest(
        id="recovery_period",
        description="Team recovering from previous bad period",
        scenario=InsightScenario.VELOCITY_GOOD,
        velocity={
            "throughput": {"current": 72, "previous": 45, "pct_change": 60.0},
            "cycle_time": {"current": Decimal("28.0"), "previous": Decimal("65.0"), "pct_change": -56.9},
            "review_time": {"current": Decimal("6.0"), "previous": Decimal("20.0"), "pct_change": -70.0},
        },
        quality={
            "revert_count": 2,
            "revert_rate": 2.8,
            "hotfix_count": 1,
            "hotfix_rate": 1.4,
            "avg_review_rounds": 1.3,
            "large_pr_pct": 15.0,
        },
        team_health={
            "active_contributors": 11,
            "pr_distribution": {"top_contributor_pct": 20.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 6.5, "max_reviews": 12},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 30,
            "non_ai_pr_count": 42,
            "ai_adoption_pct": 41.7,
            "ai_avg_cycle_time": Decimal("24.0"),
            "non_ai_avg_cycle_time": Decimal("31.0"),
            "cycle_time_difference_pct": Decimal("-22.6"),
        },
        metadata=_metadata(),
        expected_headline_contains=["60"],  # Should mention the 60% throughput surge
        expected_headline_not_contains=["concern", "crisis", "slower"],
        expected_trend="positive",
        expected_focus_metric="velocity",
        notes="60% throughput increase, 57% faster cycle time. Major recovery.",
    ),
    InsightGoldenTest(
        id="no_ai_adoption",
        description="Team not using AI tools - opportunity to adopt",
        scenario=InsightScenario.MIXED,
        velocity={
            "throughput": {"current": 40, "previous": 38, "pct_change": 5.3},
            "cycle_time": {"current": Decimal("32.0"), "previous": Decimal("30.0"), "pct_change": 6.7},
            "review_time": {"current": Decimal("8.0"), "previous": Decimal("7.0"), "pct_change": 14.3},
        },
        quality={
            "revert_count": 1,
            "revert_rate": 2.5,
            "hotfix_count": 0,
            "hotfix_rate": 0.0,
            "avg_review_rounds": 1.3,
            "large_pr_pct": 15.0,
        },
        team_health={
            "active_contributors": 8,
            "pr_distribution": {"top_contributor_pct": 28.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 5.0, "max_reviews": 10},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 2,
            "non_ai_pr_count": 38,
            "ai_adoption_pct": 5.0,
            "ai_avg_cycle_time": None,
            "non_ai_avg_cycle_time": Decimal("32.0"),
            "cycle_time_difference_pct": None,
        },
        metadata=_metadata(),
        expected_headline_contains=[],  # Stable metrics with low AI - model may focus on either
        expected_headline_not_contains=["crisis", "excellent", "major"],
        expected_trend="neutral",
        expected_focus_metric="ai_adoption",
        notes="Only 5% AI adoption but metrics stable. Model may focus on velocity or AI opportunity.",
    ),
    InsightGoldenTest(
        id="low_activity",
        description="Very low PR volume - concerning for CTO",
        scenario=InsightScenario.VELOCITY_BAD,
        velocity={
            "throughput": {"current": 8, "previous": 22, "pct_change": -63.6},
            "cycle_time": {"current": Decimal("18.0"), "previous": Decimal("24.0"), "pct_change": -25.0},
            "review_time": {"current": Decimal("4.0"), "previous": Decimal("6.0"), "pct_change": -33.3},
        },
        quality={
            "revert_count": 0,
            "revert_rate": 0.0,
            "hotfix_count": 0,
            "hotfix_rate": 0.0,
            "avg_review_rounds": 1.0,
            "large_pr_pct": 12.5,
        },
        team_health={
            "active_contributors": 3,
            "pr_distribution": {"top_contributor_pct": 50.0, "is_concentrated": False},
            "review_distribution": {"avg_reviews_per_reviewer": 2.7, "max_reviews": 5},
            "bottleneck": None,
        },
        ai_impact={
            "ai_pr_count": 3,
            "non_ai_pr_count": 5,
            "ai_adoption_pct": 37.5,
            "ai_avg_cycle_time": Decimal("16.0"),
            "non_ai_avg_cycle_time": Decimal("19.0"),
            "cycle_time_difference_pct": Decimal("-15.8"),
        },
        metadata=_metadata(),
        expected_headline_contains=["throughput"],  # 64% drop is major
        expected_headline_not_contains=["excellent", "great"],
        expected_trend="negative",
        expected_focus_metric="throughput",
        notes="Only 8 PRs merged (down 64%). Only 3 active contributors. Concerning for CTO.",
    ),
]


def get_insight_test_data(test: InsightGoldenTest) -> dict:
    """Convert golden test to format expected by generate_insight."""
    return {
        "velocity": test.velocity,
        "quality": test.quality,
        "team_health": test.team_health,
        "ai_impact": test.ai_impact,
        "metadata": test.metadata,
    }


def to_promptfoo_test(test: InsightGoldenTest) -> dict:
    """Convert golden test to promptfoo test case format."""
    vars_dict = get_insight_test_data(test)

    assertions = []

    # Add headline content checks
    for phrase in test.expected_headline_contains:
        assertions.append(
            {
                "type": "contains",
                "value": phrase.lower(),
                "transform": "output.headline.toLowerCase()",
            }
        )

    for phrase in test.expected_headline_not_contains:
        assertions.append(
            {
                "type": "not-contains",
                "value": phrase.lower(),
                "transform": "output.headline.toLowerCase()",
            }
        )

    # Check metric_cards has 4 items
    assertions.append(
        {
            "type": "javascript",
            "value": "output.metric_cards && output.metric_cards.length === 4",
        }
    )

    # Check all required fields present
    assertions.append(
        {
            "type": "javascript",
            "value": "output.headline && output.detail && output.recommendation",
        }
    )

    return {
        "description": f"{test.id}: {test.description}",
        "vars": vars_dict,
        "assert": assertions,
    }
