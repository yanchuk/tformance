"""Insight Rules - trend detection rules for AI adoption, cycle time, benchmarks, and achievements."""

from abc import abstractmethod
from datetime import date, timedelta

from apps.metrics.insights.engine import InsightResult, InsightRule
from apps.metrics.services.dashboard_service import (
    get_ai_adoption_trend,
    get_cicd_pass_rate,
    get_cycle_time_trend,
    get_revert_hotfix_stats,
    get_reviewer_correlations,
    get_unlinked_prs,
)
from apps.teams.models import Team


def get_current_week_range(target_date: date) -> tuple[date, date]:
    """Calculate date range for current week (last 7 days ending on target_date).

    Args:
        target_date: The end date of the current week

    Returns:
        Tuple of (start_date, end_date) for the current week
    """
    start_date = target_date - timedelta(days=6)
    return start_date, target_date


def get_previous_weeks_range(target_date: date, num_weeks: int) -> tuple[date, date]:
    """Calculate date range for previous weeks before current week.

    Args:
        target_date: The end date to calculate from
        num_weeks: Number of weeks to look back

    Returns:
        Tuple of (start_date, end_date) for the previous weeks period
    """
    # Previous weeks end 7 days before target_date (before current week starts)
    end_date = target_date - timedelta(days=7)
    # Previous weeks start (num_weeks * 7) days before the end
    start_date = end_date - timedelta(days=(num_weeks * 7) - 1)
    return start_date, end_date


class BaseTrendRule(InsightRule):
    """Base class for trend detection rules.

    Provides common functionality for comparing first week vs last week
    over a lookback period and generating insights when thresholds are met.
    """

    # Subclasses should override these constants
    LOOKBACK_WEEKS = 4
    MIN_WEEKS_FOR_TREND = 2

    def evaluate(self, team: Team, target_date: date) -> list[InsightResult]:
        """Evaluate trend and generate insights if threshold is met.

        Args:
            team: The team to analyze
            target_date: The date to analyze for

        Returns:
            List of InsightResult instances (may be empty if no insights found)
        """
        # Calculate date range
        end_date = target_date
        start_date = target_date - timedelta(weeks=self.LOOKBACK_WEEKS)

        # Get trend data from subclass
        trend_data = self._get_trend_data(team, start_date, end_date)

        # Validate sufficient data
        if len(trend_data) < self.MIN_WEEKS_FOR_TREND:
            return []

        # Extract values
        first_week_value = trend_data[0]["value"]
        last_week_value = trend_data[-1]["value"]

        # Calculate change and check threshold
        change = self._calculate_change(first_week_value, last_week_value)
        if change is None or not self._meets_threshold(change):
            return []

        # Generate insight from subclass
        return self._generate_insight(trend_data, first_week_value, last_week_value, change)

    @abstractmethod
    def _get_trend_data(self, team: Team, start_date: date, end_date: date) -> list[dict]:
        """Fetch trend data for the date range.

        Args:
            team: The team to analyze
            start_date: Start of the period
            end_date: End of the period

        Returns:
            List of trend data dictionaries with 'value' key
        """
        pass

    @abstractmethod
    def _calculate_change(self, first_value: float, last_value: float) -> float | None:
        """Calculate change between first and last values.

        Args:
            first_value: Value from first week
            last_value: Value from last week

        Returns:
            Change value or None if calculation not possible
        """
        pass

    @abstractmethod
    def _meets_threshold(self, change: float) -> bool:
        """Check if change meets the threshold for generating an insight.

        Args:
            change: The calculated change value

        Returns:
            True if threshold is met, False otherwise
        """
        pass

    @abstractmethod
    def _generate_insight(
        self,
        trend_data: list[dict],
        first_value: float,
        last_value: float,
        change: float,
    ) -> list[InsightResult]:
        """Generate insight result.

        Args:
            trend_data: Full trend data
            first_value: Value from first week
            last_value: Value from last week
            change: Calculated change value

        Returns:
            List containing single InsightResult
        """
        pass


class AIAdoptionTrendRule(BaseTrendRule):
    """Detect significant changes in AI adoption percentage.

    Compares AI adoption in the first week vs last week of a 4-week lookback period.
    Generates an insight if the change is >= 10%.
    """

    CHANGE_THRESHOLD = 10  # percentage points

    def _get_trend_data(self, team: Team, start_date: date, end_date: date) -> list[dict]:
        """Fetch AI adoption trend data."""
        return get_ai_adoption_trend(team, start_date, end_date)

    def _calculate_change(self, first_value: float, last_value: float) -> float | None:
        """Calculate absolute change in percentage points."""
        return last_value - first_value

    def _meets_threshold(self, change: float) -> bool:
        """Check if change exceeds threshold (strictly greater than 10%)."""
        return abs(change) > self.CHANGE_THRESHOLD

    def _generate_insight(
        self,
        trend_data: list[dict],
        first_value: float,
        last_value: float,
        change: float,
    ) -> list[InsightResult]:
        """Generate AI adoption trend insight."""
        direction = "increased" if change > 0 else "decreased"
        title = f"AI adoption {direction} {abs(change):.0f}%"
        description = (
            f"AI adoption has {direction} from {first_value:.0f}% to {last_value:.0f}% "
            f"over the past {self.LOOKBACK_WEEKS} weeks."
        )

        return [
            InsightResult(
                category="trend",
                priority="medium",
                title=title,
                description=description,
                metric_type="ai_adoption",
                metric_value={"trend": trend_data, "change": change},
                comparison_period="4_weeks",
            )
        ]


class CycleTimeTrendRule(BaseTrendRule):
    """Detect significant changes in cycle time.

    Compares cycle time in the first week vs last week of a 4-week lookback period.
    Generates an insight if the change is >= 20%.
    """

    CHANGE_THRESHOLD = 20  # percent

    def _get_trend_data(self, team: Team, start_date: date, end_date: date) -> list[dict]:
        """Fetch cycle time trend data."""
        return get_cycle_time_trend(team, start_date, end_date)

    def _calculate_change(self, first_value: float, last_value: float) -> float | None:
        """Calculate percentage change, return None if first value is zero."""
        if first_value == 0:
            return None
        return ((last_value - first_value) / first_value) * 100

    def _meets_threshold(self, change: float) -> bool:
        """Check if change exceeds threshold (20%)."""
        return abs(change) >= self.CHANGE_THRESHOLD

    def _generate_insight(
        self,
        trend_data: list[dict],
        first_value: float,
        last_value: float,
        change: float,
    ) -> list[InsightResult]:
        """Generate cycle time trend insight."""
        # Negative change = improvement (cycle time decreased)
        # Positive change = regression (cycle time increased)
        if change < 0:
            direction = "improved"
            priority = "medium"
        else:
            direction = "regressed"
            priority = "high"

        title = f"Cycle time {direction} {abs(change):.0f}%"
        description = (
            f"Cycle time has {direction} from {first_value:.0f} hours to {last_value:.0f} hours "
            f"over the past {self.LOOKBACK_WEEKS} weeks."
        )

        return [
            InsightResult(
                category="trend",
                priority=priority,
                title=title,
                description=description,
                metric_type="cycle_time",
                metric_value={"trend": trend_data, "change": change},
                comparison_period="4_weeks",
            )
        ]


class HotfixSpikeRule(InsightRule):
    """Detect spikes in hotfix activity.

    Generates an insight if current week hotfixes are 3x or more above
    the 4-week average.
    """

    SPIKE_THRESHOLD = 3.0  # 3x multiplier

    def evaluate(self, team: Team, target_date: date) -> list[InsightResult]:
        """Evaluate hotfix spike and generate insight if threshold is met.

        Args:
            team: The team to analyze
            target_date: The date to analyze for

        Returns:
            List of InsightResult instances (may be empty if no insights found)
        """
        # Current week: last 7 days ending on target_date
        current_week_start, current_week_end = get_current_week_range(target_date)

        # Previous 4 weeks: 28 days before current week
        previous_weeks_start, previous_weeks_end = get_previous_weeks_range(target_date, num_weeks=4)

        # Get current week stats
        current_stats = get_revert_hotfix_stats(team, current_week_start, current_week_end)
        current_hotfixes = current_stats["hotfix_count"]

        # Get previous 4 weeks stats
        previous_stats = get_revert_hotfix_stats(team, previous_weeks_start, previous_weeks_end)
        previous_hotfixes = previous_stats["hotfix_count"]

        # Calculate average hotfixes per week over previous 4 weeks
        previous_average = previous_hotfixes / 4.0

        # Check if current week is 3x or more above average
        if previous_average > 0 and current_hotfixes >= self.SPIKE_THRESHOLD * previous_average:
            title = f"Hotfix spike detected: {current_hotfixes} hotfixes (avg: {previous_average:.1f})"
            description = (
                f"Current week has {current_hotfixes} hotfixes, which is {current_hotfixes / previous_average:.1f}x "
                f"higher than the 4-week average of {previous_average:.1f} hotfixes per week. "
                f"This spike may indicate quality issues that need investigation."
            )

            return [
                InsightResult(
                    category="anomaly",
                    priority="high",
                    title=title,
                    description=description,
                    metric_type="hotfix_spike",
                    metric_value={
                        "current_week": current_hotfixes,
                        "previous_average": previous_average,
                        "multiplier": current_hotfixes / previous_average,
                    },
                    comparison_period="4_weeks",
                )
            ]

        return []


class RevertSpikeRule(InsightRule):
    """Detect reverts in the current week.

    Generates an insight if any reverts are detected in the current week.
    """

    def evaluate(self, team: Team, target_date: date) -> list[InsightResult]:
        """Evaluate revert activity and generate insight if reverts detected.

        Args:
            team: The team to analyze
            target_date: The date to analyze for

        Returns:
            List of InsightResult instances (may be empty if no insights found)
        """
        # Current week: last 7 days ending on target_date
        current_week_start, current_week_end = get_current_week_range(target_date)

        # Get current week stats
        stats = get_revert_hotfix_stats(team, current_week_start, current_week_end)
        revert_count = stats["revert_count"]

        # Generate insight if there are any reverts
        if revert_count > 0:
            title = f"{revert_count} reverts this week - investigate quality issues"
            description = (
                f"Detected {revert_count} revert{'s' if revert_count != 1 else ''} this week. "
                f"Reverts indicate code that had to be rolled back, which may suggest "
                f"quality issues, insufficient testing, or rushed deployments."
            )

            return [
                InsightResult(
                    category="anomaly",
                    priority="high",
                    title=title,
                    description=description,
                    metric_type="revert_spike",
                    metric_value={"revert_count": revert_count},
                    comparison_period="1_week",
                )
            ]

        return []


class CIFailureRateRule(InsightRule):
    """Detect high CI/CD failure rates.

    Generates an insight if the CI failure rate exceeds 20%.
    """

    FAILURE_THRESHOLD = 20.0  # percent

    def evaluate(self, team: Team, target_date: date) -> list[InsightResult]:
        """Evaluate CI failure rate and generate insight if threshold exceeded.

        Args:
            team: The team to analyze
            target_date: The date to analyze for

        Returns:
            List of InsightResult instances (may be empty if no insights found)
        """
        # Last 4 weeks: target_date - 28 days to target_date
        start_date = target_date - timedelta(days=28)
        end_date = target_date

        # Get CI/CD stats
        stats = get_cicd_pass_rate(team, start_date, end_date)
        total_runs = stats["total_runs"]
        pass_rate = float(stats["pass_rate"])

        # No insight if no data
        if total_runs == 0:
            return []

        # Calculate failure rate
        failure_rate = 100.0 - pass_rate

        # Generate insight if failure rate exceeds threshold
        if failure_rate > self.FAILURE_THRESHOLD:
            title = f"CI/CD failure rate at {failure_rate:.0f}% (above 20% threshold)"
            description = (
                f"CI/CD failure rate is {failure_rate:.0f}% over the past 4 weeks "
                f"({stats['failure_count']} failures out of {total_runs} runs). "
                f"This is above the 20% threshold and may indicate infrastructure issues, "
                f"flaky tests, or code quality problems."
            )

            return [
                InsightResult(
                    category="anomaly",
                    priority="medium",
                    title=title,
                    description=description,
                    metric_type="ci_failure_rate",
                    metric_value={
                        "failure_rate": failure_rate,
                        "total_runs": total_runs,
                        "failure_count": stats["failure_count"],
                        "success_count": stats["success_count"],
                    },
                    comparison_period="4_weeks",
                )
            ]

        return []


class RedundantReviewerRule(InsightRule):
    """Detect redundant reviewer pairs.

    Generates insights for reviewer pairs that show 95%+ agreement on 10+ PRs.
    Reports up to 3 most redundant pairs.
    """

    MAX_PAIRS_TO_REPORT = 3

    def evaluate(self, team: Team, target_date: date) -> list[InsightResult]:
        """Evaluate redundant reviewer pairs and generate insights.

        Args:
            team: The team to analyze
            target_date: The date to analyze for (unused, analysis is all-time)

        Returns:
            List of InsightResult instances (up to 3, may be empty if no insights found)
        """
        # Get reviewer correlations from dashboard service
        correlations = get_reviewer_correlations(team)

        # Filter for redundant pairs only
        redundant_pairs = [c for c in correlations if c["is_redundant"]]

        # Limit to max pairs to report
        redundant_pairs = redundant_pairs[: self.MAX_PAIRS_TO_REPORT]

        # Generate insights for each redundant pair
        insights = []
        for pair in redundant_pairs:
            reviewer_1 = pair["reviewer_1_name"]
            reviewer_2 = pair["reviewer_2_name"]
            agreement_rate = float(pair["agreement_rate"])

            title = f"Redundant reviewers: {reviewer_1} & {reviewer_2} agree {agreement_rate:.0f}% of the time"
            description = (
                f"{reviewer_1} and {reviewer_2} have reviewed {pair['prs_reviewed_together']} PRs together "
                f"and agree {agreement_rate:.0f}% of the time. Consider redistributing review load "
                f"to get more diverse perspectives."
            )

            insights.append(
                InsightResult(
                    category="action",
                    priority="low",
                    title=title,
                    description=description,
                    metric_type="redundant_reviewers",
                    metric_value={
                        "reviewer_1": reviewer_1,
                        "reviewer_2": reviewer_2,
                        "agreement_rate": agreement_rate,
                        "prs_reviewed_together": pair["prs_reviewed_together"],
                    },
                    comparison_period="all_time",
                )
            )

        return insights


class UnlinkedPRsRule(InsightRule):
    """Detect PRs missing Jira links.

    Generates an insight if 5+ PRs in the last 4 weeks lack Jira issue links.
    """

    LOOKBACK_WEEKS = 4
    THRESHOLD = 5

    def evaluate(self, team: Team, target_date: date) -> list[InsightResult]:
        """Evaluate unlinked PRs and generate insight if threshold met.

        Args:
            team: The team to analyze
            target_date: The date to analyze for

        Returns:
            List of InsightResult instances (may be empty if no insights found)
        """
        # Look back 4 weeks from target_date
        start_date = target_date - timedelta(weeks=self.LOOKBACK_WEEKS)
        end_date = target_date

        # Get unlinked PRs (don't limit, we need count)
        unlinked_prs = get_unlinked_prs(team, start_date, end_date, limit=1000)
        count = len(unlinked_prs)

        # Generate insight if count meets threshold
        if count >= self.THRESHOLD:
            title = f"{count} PRs missing Jira links - consider enforcing"
            description = (
                f"Found {count} merged PRs in the past {self.LOOKBACK_WEEKS} weeks without Jira issue links. "
                f"Consider enforcing Jira links in your PR workflow to improve traceability "
                f"and project management visibility."
            )

            return [
                InsightResult(
                    category="action",
                    priority="low",
                    title=title,
                    description=description,
                    metric_type="unlinked_prs",
                    metric_value={"count": count, "lookback_weeks": self.LOOKBACK_WEEKS},
                    comparison_period=f"{self.LOOKBACK_WEEKS}_weeks",
                )
            ]

        return []


class BenchmarkComparisonRule(InsightRule):
    """Compare team metrics against industry benchmarks.

    Generates insights when team performance is:
    - Elite (top 25%): Positive reinforcement
    - Needs improvement (bottom 10%): Actionable recommendations
    """

    def evaluate(self, team: Team, target_date: date) -> list[InsightResult]:
        """Evaluate team against benchmarks and generate insights.

        Args:
            team: The team to analyze
            target_date: The date to analyze for

        Returns:
            List of InsightResult instances (may be empty if no insights found)
        """
        from apps.metrics.services import benchmark_service

        insights = []

        # Get cycle time benchmark
        result = benchmark_service.get_benchmark_for_team(team, "cycle_time", days=30)

        if result.get("team_value") is not None and result.get("percentile") is not None:
            percentile = result["percentile"]
            team_value = result["team_value"]
            benchmark = result.get("benchmark", {})

            # Elite performance (top 25%)
            if percentile >= 75:
                insights.append(
                    InsightResult(
                        category="comparison",
                        priority="low",
                        title=f"Elite performance: Top {100 - percentile}% for cycle time",
                        description=(
                            f"Your team's cycle time of {team_value:.1f}h puts you in the "
                            "elite category compared to industry benchmarks."
                        ),
                        metric_type="cycle_time",
                        metric_value={
                            "value": float(team_value),
                            "percentile": percentile,
                            "benchmark_p50": benchmark.get("p50"),
                        },
                        comparison_period="30_days",
                    )
                )
            # Needs improvement (bottom 10%)
            elif percentile <= 10:
                p50 = benchmark.get("p50", 0)
                insights.append(
                    InsightResult(
                        category="comparison",
                        priority="high",
                        title="Opportunity to improve cycle time",
                        description=(
                            f"Your team's cycle time of {team_value:.1f}h is above the "
                            f"industry median of {p50:.1f}h. Consider smaller PRs or async reviews."
                        ),
                        metric_type="cycle_time",
                        metric_value={
                            "value": float(team_value),
                            "percentile": percentile,
                            "benchmark_p50": p50,
                        },
                        comparison_period="30_days",
                    )
                )

        return insights


class AchievementMilestoneRule(InsightRule):
    """Detect achievement milestones for AI adoption and PR count.

    Generates insights when team reaches:
    - AI adoption milestones: 25%, 50%, 75%, 90%
    - PR count milestones: 50, 100, 250, 500, 1000
    """

    AI_ADOPTION_MILESTONES = [25, 50, 75, 90]
    PR_COUNT_MILESTONES = [50, 100, 250, 500, 1000]

    def evaluate(self, team: Team, target_date: date) -> list[InsightResult]:
        """Evaluate milestones and generate insights.

        Args:
            team: The team to analyze
            target_date: The date to analyze for

        Returns:
            List of InsightResult instances (may be empty if no insights found)
        """
        from apps.metrics.models import PullRequest

        insights = []

        # Get all-time stats
        total_prs = PullRequest.objects.filter(team=team, state="merged").count()
        ai_prs = PullRequest.objects.filter(team=team, state="merged", is_ai_assisted=True).count()

        if total_prs == 0:
            return insights

        # AI adoption milestone
        ai_pct = (ai_prs / total_prs) * 100
        for milestone in self.AI_ADOPTION_MILESTONES:
            if ai_pct >= milestone and ai_pct < milestone + 5:
                insights.append(
                    InsightResult(
                        category="action",
                        priority="low",
                        title=f"AI adoption milestone: {milestone}% reached!",
                        description=f"Congratulations! {ai_pct:.0f}% of your PRs are now AI-assisted.",
                        metric_type="ai_adoption",
                        metric_value={
                            "value": float(ai_pct),
                            "milestone": milestone,
                            "total_prs": total_prs,
                            "ai_prs": ai_prs,
                        },
                        comparison_period="all_time",
                    )
                )
                break

        # PR count milestone
        for milestone in self.PR_COUNT_MILESTONES:
            if total_prs >= milestone and total_prs < milestone + 10:
                insights.append(
                    InsightResult(
                        category="action",
                        priority="low",
                        title=f"Milestone: {milestone} PRs merged!",
                        description=f"Your team has merged {total_prs} pull requests. Keep up the great work!",
                        metric_type="pr_count",
                        metric_value={
                            "value": total_prs,
                            "milestone": milestone,
                        },
                        comparison_period="all_time",
                    )
                )
                break

        return insights
