"""
Metrics models - split into domain-specific modules.

All models are re-exported here for backward compatibility.
Import as: from apps.metrics.models import PullRequest

Module Structure:
- team.py: TeamMember
- pull_requests.py: PullRequest (core PR entity)
- github.py: PRReview, PRCheckRun, PRFile, PRComment, Commit
- jira.py: JiraIssue
- surveys.py: PRSurvey, PRSurveyReview
- aggregations.py: AIUsageDaily, WeeklyMetrics, ReviewerCorrelation
- insights.py: DailyInsight
- deployments.py: Deployment
- benchmarks.py: IndustryBenchmark
"""

from .aggregations import (
    AIUsageDaily,
    CopilotEditorDaily,
    CopilotLanguageDaily,
    CopilotSeatSnapshot,
    ReviewerCorrelation,
    WeeklyMetrics,
)
from .benchmarks import IndustryBenchmark
from .deployments import Deployment
from .github import Commit, PRCheckRun, PRComment, PRFile, PRReview
from .insights import DailyInsight
from .jira import JiraIssue
from .pull_requests import PullRequest
from .surveys import PRSurvey, PRSurveyReview
from .team import TeamMember

__all__ = [
    # Team
    "TeamMember",
    # GitHub
    "PullRequest",
    "PRReview",
    "PRCheckRun",
    "PRFile",
    "PRComment",
    "Commit",
    # Jira
    "JiraIssue",
    # Surveys
    "PRSurvey",
    "PRSurveyReview",
    # Aggregations
    "AIUsageDaily",
    "CopilotEditorDaily",
    "CopilotLanguageDaily",
    "WeeklyMetrics",
    "ReviewerCorrelation",
    "CopilotSeatSnapshot",
    # Insights
    "DailyInsight",
    # Deployments
    "Deployment",
    # Benchmarks
    "IndustryBenchmark",
]
