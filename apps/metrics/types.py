"""Type definitions for metrics services.

This module provides TypedDict definitions for structured data passed between
metrics service functions. Using these types:

1. Enables better IDE autocomplete and navigation
2. Catches type errors at development time (via pyright)
3. Documents expected data structures inline
4. Improves AI coding agent understanding of code

Usage:
    from apps.metrics.types import InsightData, InsightResponse, MetricCard

    def generate_insight(data: InsightData) -> InsightResponse:
        ...
"""

from __future__ import annotations

from typing import Literal, TypedDict


# =============================================================================
# Metric Card Types (used in insight UI)
# =============================================================================
class MetricCard(TypedDict):
    """A single metric card displayed in the insight UI.

    Attributes:
        label: Display name (e.g., "Throughput", "Cycle Time")
        value: Formatted value string (e.g., "+15.2%", "24.5h")
        trend: Visual indicator for the metric direction
    """

    label: str
    value: str
    trend: Literal["positive", "negative", "neutral", "warning"]


# =============================================================================
# Insight Response Types (LLM output)
# =============================================================================
class InsightAction(TypedDict):
    """An action button in the insight response.

    Attributes:
        action_type: One of the predefined action types for URL generation
        label: Button text displayed to user
    """

    action_type: Literal[
        "view_ai_prs",
        "view_non_ai_prs",
        "view_slow_prs",
        "view_reverts",
        "view_large_prs",
        "view_contributors",
        "view_review_bottlenecks",
    ]
    label: str


class InsightResponse(TypedDict, total=False):
    """Full insight response from LLM or fallback.

    Attributes:
        headline: 6-10 word root cause summary (no numbers)
        detail: 2-4 bullet points explaining what's happening
        recommendation: One actionable sentence with @/@@ mentions
        actions: 2-3 action buttons matching issues in detail
        metric_cards: Pre-computed metric cards (not from LLM)
        is_fallback: True if rule-based fallback was used
    """

    headline: str
    detail: str
    recommendation: str
    actions: list[InsightAction]
    metric_cards: list[MetricCard]
    is_fallback: bool


# =============================================================================
# Contributor Types
# =============================================================================
class ContributorInfo(TypedDict):
    """Information about a top contributor.

    Attributes:
        github_username: GitHub username for @mentions
        display_name: Human-readable name
        pr_count: Number of PRs authored in period
        pct_share: Percentage of total team PRs
    """

    github_username: str
    display_name: str
    pr_count: int
    pct_share: float


# =============================================================================
# Velocity Metrics Types
# =============================================================================
class ThroughputMetrics(TypedDict, total=False):
    """Throughput comparison metrics.

    Attributes:
        current: PRs merged in current period
        previous: PRs merged in previous period
        pct_change: Percentage change from previous
    """

    current: int
    previous: int
    pct_change: float | None


class CycleTimeMetrics(TypedDict, total=False):
    """Cycle time comparison metrics (in hours).

    Attributes:
        current: Average cycle time in current period
        previous: Average cycle time in previous period
        pct_change: Percentage change from previous
    """

    current: float | None
    previous: float | None
    pct_change: float | None


class ReviewTimeMetrics(TypedDict, total=False):
    """Review time comparison metrics (in hours).

    Attributes:
        current: Average time to first review in current period
        previous: Average time to first review in previous period
        pct_change: Percentage change from previous
    """

    current: float | None
    previous: float | None
    pct_change: float | None


class VelocityMetrics(TypedDict, total=False):
    """Combined velocity metrics from get_velocity_comparison.

    Attributes:
        throughput: PR throughput with period comparison
        cycle_time: Cycle time with period comparison
        review_time: Time to first review with period comparison
    """

    throughput: ThroughputMetrics
    cycle_time: CycleTimeMetrics
    review_time: ReviewTimeMetrics


# =============================================================================
# Quality Metrics Types
# =============================================================================
class QualityMetrics(TypedDict, total=False):
    """Quality metrics from get_quality_metrics.

    Attributes:
        revert_count: Number of reverted PRs
        revert_rate: Percentage of PRs that were reverted
        hotfix_count: Number of hotfix PRs
        avg_review_rounds: Average review iterations per PR
        large_pr_pct: Percentage of PRs over 400 lines
    """

    revert_count: int
    revert_rate: float
    hotfix_count: int
    avg_review_rounds: float
    large_pr_pct: float


# =============================================================================
# AI Impact Metrics Types
# =============================================================================
class AIImpactMetrics(TypedDict, total=False):
    """AI impact metrics from get_ai_impact_stats.

    Attributes:
        ai_pr_count: Number of AI-assisted PRs
        non_ai_pr_count: Number of non-AI PRs
        ai_adoption_pct: Percentage of PRs using AI tools
        ai_avg_cycle_time: Average cycle time for AI PRs (hours)
        non_ai_avg_cycle_time: Average cycle time for non-AI PRs (hours)
        cycle_time_difference_pct: Percentage difference in cycle time
    """

    ai_pr_count: int
    non_ai_pr_count: int
    ai_adoption_pct: float
    ai_avg_cycle_time: float | None
    non_ai_avg_cycle_time: float | None
    cycle_time_difference_pct: float | None


# =============================================================================
# Team Health Metrics Types
# =============================================================================
class ReviewerDistribution(TypedDict):
    """Review workload distribution for a single reviewer.

    Attributes:
        username: GitHub username
        review_count: Number of reviews completed
        pct_share: Percentage of total team reviews
    """

    username: str
    review_count: int
    pct_share: float


class TeamHealthMetrics(TypedDict, total=False):
    """Team health metrics from get_team_health_metrics.

    Attributes:
        active_contributors: Number of active PR authors
        review_distribution: Review workload by team member
        bus_factor: Minimum contributors for 50% of work
        top_contributors: Top PR authors with GitHub usernames
    """

    active_contributors: int
    review_distribution: list[ReviewerDistribution]
    bus_factor: int
    top_contributors: list[ContributorInfo]


# =============================================================================
# Copilot Metrics Types
# =============================================================================
class CopilotMetrics(TypedDict, total=False):
    """Copilot usage metrics for LLM prompt.

    Attributes:
        total_suggestions: Total code suggestions shown
        total_acceptances: Total suggestions accepted
        acceptance_rate: Acceptance rate as percentage
        active_users: Users with Copilot activity
        total_seats: Total Copilot licenses
    """

    total_suggestions: int
    total_acceptances: int
    acceptance_rate: float
    active_users: int
    total_seats: int


# =============================================================================
# Jira Metrics Types
# =============================================================================
class JiraSprintMetrics(TypedDict, total=False):
    """Jira sprint metrics for LLM prompt."""

    velocity: float | None
    commitment_accuracy: float | None
    scope_change: float | None


class JiraCorrelation(TypedDict, total=False):
    """PR-Jira correlation metrics."""

    linked_prs: int
    unlinked_prs: int
    linkage_rate: float


class JiraMetrics(TypedDict, total=False):
    """Combined Jira metrics for insight generation.

    Attributes:
        sprint_metrics: Sprint velocity and commitment
        pr_correlation: PR-Jira linkage stats
        linkage_trend: Historical linkage trend
        velocity_trend: Historical velocity trend
    """

    sprint_metrics: JiraSprintMetrics
    pr_correlation: JiraCorrelation
    linkage_trend: list[dict]  # Historical data points
    velocity_trend: list[dict]  # Historical data points


# =============================================================================
# Insight Data Types (input to LLM)
# =============================================================================
class InsightMetadata(TypedDict):
    """Metadata about the insight period.

    Attributes:
        start_date: ISO format start date
        end_date: ISO format end date
        days: Number of days in period
        team_name: Name of the team
    """

    start_date: str
    end_date: str
    days: int
    team_name: str


class InsightData(TypedDict, total=False):
    """Full data structure passed to insight generation.

    This is the main input type for build_insight_prompt() and generate_insight().
    All metrics domains are optional to support partial data availability.

    Attributes:
        velocity: Throughput, cycle time, review time comparisons
        quality: Revert rate, hotfixes, review rounds, large PRs
        team_health: Contributors, review distribution, bus factor
        ai_impact: AI adoption rate and cycle time comparison
        jira: Optional Jira sprint and correlation metrics
        copilot_metrics: Optional Copilot usage metrics
        metadata: Period info and team name
    """

    velocity: VelocityMetrics
    quality: QualityMetrics
    team_health: TeamHealthMetrics
    ai_impact: AIImpactMetrics
    jira: JiraMetrics | None
    copilot_metrics: CopilotMetrics | None
    metadata: InsightMetadata


# =============================================================================
# PR Context Types (for LLM prompt generation)
# =============================================================================
class PRContext(TypedDict, total=False):
    """PR context for LLM prompt generation.

    Replaces 26 individual parameters in get_user_prompt() with a single typed dict.
    All fields are optional except pr_body which is the minimum required content.

    Usage:
        context: PRContext = {
            "pr_body": "Add new feature...",
            "pr_title": "feat: add dark mode",
            "author_name": "johndoe",
        }
        prompt = get_user_prompt_v2(context)

    Attributes:
        # === Basic Info ===
        pr_body: The PR description text (primary content for analysis)
        pr_title: The PR title
        repo_name: Full repository path (e.g., "anthropics/cookbook")
        author_name: PR author's display name

        # === Code Changes ===
        file_count: Number of files changed
        additions: Lines added
        deletions: Lines deleted
        file_paths: List of changed file paths (for tech detection)
        repo_languages: Top languages from repository (e.g., ["Python", "TypeScript"])

        # === State & Flags ===
        state: PR state (open, merged, closed)
        is_draft: Whether PR is a draft
        is_hotfix: Whether PR is marked as hotfix
        is_revert: Whether PR is a revert
        labels: List of label names

        # === Timing Metrics ===
        cycle_time_hours: Time from open to merge
        review_time_hours: Time from open to first review

        # === Collaboration ===
        comment_count: Number of comments
        commits_after_first_review: Number of commits after first review
        review_rounds: Number of review cycles
        commit_messages: List of commit messages (for AI co-author detection)
        reviewers: List of reviewer names
        review_comments: List of review comment bodies (sample)

        # === Project Management ===
        milestone: Milestone title (e.g., "Q1 2025 Release")
        assignees: List of assignee usernames
        linked_issues: List of linked issue references (e.g., ["#123", "#456"])
        jira_key: Jira issue key (e.g., "PROJ-1234")
    """

    # === Basic Info ===
    pr_body: str  # Primary content - effectively required for meaningful analysis
    pr_title: str
    repo_name: str
    author_name: str

    # === Code Changes ===
    file_count: int
    additions: int
    deletions: int
    file_paths: list[str]
    repo_languages: list[str]

    # === State & Flags ===
    state: str
    is_draft: bool
    is_hotfix: bool
    is_revert: bool
    labels: list[str]

    # === Timing Metrics ===
    cycle_time_hours: float
    review_time_hours: float

    # === Collaboration ===
    comment_count: int
    commits_after_first_review: int
    review_rounds: int
    commit_messages: list[str]
    reviewers: list[str]
    review_comments: list[str]

    # === Project Management ===
    milestone: str
    assignees: list[str]
    linked_issues: list[str]
    jira_key: str
