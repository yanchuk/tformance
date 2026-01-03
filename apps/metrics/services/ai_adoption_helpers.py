"""AI Adoption data source helpers.

Controls whether AI adoption metrics use survey data or detection data
based on the `rely_on_surveys_for_ai_adoption` feature flag.

When flag is False (default): Use only LLM and pattern detection
When flag is True: Use survey data with fallback to detection
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from waffle import flag_is_active

if TYPE_CHECKING:
    from django.http import HttpRequest

    from apps.metrics.models import PullRequest
    from apps.teams.models import Team

# Feature flag name for AI adoption data source
AI_ADOPTION_SURVEY_FLAG = "rely_on_surveys_for_ai_adoption"


def should_use_survey_data(request_or_team: HttpRequest | Team) -> bool:
    """Check if AI adoption should use survey data.

    Args:
        request_or_team: HttpRequest (with team attribute) or Team instance

    Returns:
        True if surveys should be primary source, False for detection-only
    """
    # Check if it's a request object with team attribute
    if hasattr(request_or_team, "user") and hasattr(request_or_team, "team"):
        return flag_is_active(request_or_team, AI_ADOPTION_SURVEY_FLAG)

    # It's a Team object - create mock request for flag check
    from django.test import RequestFactory

    from apps.teams.models import Team

    team = request_or_team
    if not isinstance(team, Team):
        return False

    request = RequestFactory().get("/")
    request.team = team
    # Get any user from the team for the request
    first_member = team.members.first()
    if first_member:
        request.user = first_member
    else:
        # Create anonymous-like user attribute
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()

    return flag_is_active(request, AI_ADOPTION_SURVEY_FLAG)


def get_pr_ai_status(pr: PullRequest, use_surveys: bool) -> bool:
    """Get AI assisted status for a PR based on data source.

    Args:
        pr: PullRequest instance
        use_surveys: Whether to check survey data first

    Returns:
        True if PR is AI-assisted, False otherwise
    """
    if use_surveys:
        # Try to get survey data first
        from apps.metrics.models import PRSurvey

        try:
            survey = pr.survey
            if survey.author_ai_assisted is not None:
                return survey.author_ai_assisted
        except PRSurvey.DoesNotExist:
            pass
        except AttributeError:
            # survey relation doesn't exist
            pass

    # Use detection (or fallback when survey unavailable)
    return pr.effective_is_ai_assisted
