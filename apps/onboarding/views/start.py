"""Start and completion views for the onboarding wizard.

Contains views for the initial start page, skip functionality, and completion page.
"""

import logging

from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from apps.onboarding.services.notifications import send_welcome_email
from apps.teams.helpers import get_next_unique_team_slug
from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN
from apps.utils.analytics import group_identify, track_event

from ._helpers import (
    ONBOARDING_ORGS_KEY,
    ONBOARDING_SELECTED_ORG_KEY,
    ONBOARDING_TOKEN_KEY,
    _get_onboarding_flags_context,
)

logger = logging.getLogger(__name__)


@login_required
def onboarding_start(request):
    """Start of onboarding wizard - prompts user to connect GitHub."""
    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        # Redirect to /app/ which auto-selects the team
        return redirect("web:home")

    # Check if user has a GitHub social account (signed up via GitHub OAuth)
    has_github_social = SocialAccount.objects.filter(user=request.user, provider="github").exists()

    return render(
        request,
        "onboarding/start.html",
        {
            "page_title": _("Connect GitHub"),
            "step": 1,
            "has_github_social": has_github_social,
            **_get_onboarding_flags_context(request),
        },
    )


@login_required
def skip_onboarding(request):
    """Allow users to skip GitHub connection and create a basic team.

    Creates a team using the user's email prefix as the team name.
    The user can connect GitHub later from the integrations settings.
    """
    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        return redirect("web:home")

    # Create team from user's email prefix
    email_prefix = request.user.email.split("@")[0]
    team_name = f"{email_prefix}'s Team"
    team_slug = get_next_unique_team_slug(team_name)

    team = Team.objects.create(name=team_name, slug=team_slug)

    # Add user as admin
    Membership.objects.create(team=team, user=request.user, role=ROLE_ADMIN)

    # Send welcome email (fail silently to not block onboarding)
    try:
        send_welcome_email(team, request.user)
    except Exception as e:
        logger.warning(f"Failed to send welcome email during onboarding skip: {e}")

    # Clear any onboarding session data
    request.session.pop(ONBOARDING_TOKEN_KEY, None)
    request.session.pop(ONBOARDING_ORGS_KEY, None)
    request.session.pop(ONBOARDING_SELECTED_ORG_KEY, None)

    # Track onboarding skip in PostHog
    group_identify(team)
    track_event(
        request.user,
        "onboarding_skipped",
        {"step": "github", "team_slug": team.slug, "reason": "skip_button"},
    )

    messages.success(
        request,
        _("Team '{}' created! Connect GitHub from Integrations to unlock all features.").format(team_name),
    )
    return redirect("web:home")


@login_required
def onboarding_complete(request):
    """Final step showing sync status and dashboard link."""
    from apps.integrations.models import JiraIntegration, SlackIntegration

    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Clear onboarding session data
    request.session.pop(ONBOARDING_SELECTED_ORG_KEY, None)

    # Get sync task info for progress indicator
    sync_task_id = request.session.get("sync_task_id")

    # Check integration status
    jira_connected = JiraIntegration.objects.filter(team=team).exists()
    slack_connected = SlackIntegration.objects.filter(team=team).exists()

    # Mark onboarding as complete
    if not team.onboarding_complete:
        team.onboarding_complete = True
        team.save(update_fields=["onboarding_complete"])

    # Track onboarding completion
    track_event(
        request.user,
        "onboarding_completed",
        {"team_slug": team.slug},
    )

    return render(
        request,
        "onboarding/complete.html",
        {
            "team": team,
            "page_title": _("Setup Complete"),
            "step": 5,
            "sync_task_id": sync_task_id,
            "jira_sync_task_id": request.session.get("jira_sync_task_id"),
            "jira_connected": jira_connected,
            "slack_connected": slack_connected,
            **_get_onboarding_flags_context(request),
        },
    )
