"""Slack-related onboarding views.

Contains views for Slack OAuth connection and configuration.
"""

import logging
from datetime import time
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.integrations.services.integration_flags import is_integration_enabled
from apps.utils.analytics import track_event

from ._helpers import _get_onboarding_flags_context

logger = logging.getLogger(__name__)


@login_required
def connect_slack(request):
    """Optional step to connect Slack.

    If the integration_slack_enabled flag is off, automatically skip to complete.
    """
    from apps.auth.oauth_state import FLOW_TYPE_SLACK_ONBOARDING, create_oauth_state
    from apps.integrations.models import SlackIntegration
    from apps.integrations.services.slack_oauth import SLACK_OAUTH_AUTHORIZE_URL, SLACK_OAUTH_SCOPES

    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Check if Slack integration is enabled via feature flag
    if not is_integration_enabled(request, "slack"):
        # Skip to complete
        return redirect("onboarding:complete")

    # Check if Slack is already connected
    slack_integration = SlackIntegration.objects.filter(team=team).first()

    # Handle OAuth initiation
    if request.GET.get("action") == "connect":
        # Create OAuth state with team_id
        state = create_oauth_state(FLOW_TYPE_SLACK_ONBOARDING, team_id=team.id)

        # Build callback URL
        callback_url = request.build_absolute_uri(reverse("tformance_auth:slack_callback"))

        # Build Slack OAuth authorization URL
        params = {
            "client_id": settings.SLACK_CLIENT_ID,
            "scope": SLACK_OAUTH_SCOPES,
            "redirect_uri": callback_url,
            "state": state,
        }
        auth_url = f"{SLACK_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

        return redirect(auth_url)

    if request.method == "POST":
        if slack_integration:
            # Save Slack configuration
            # Update feature toggles (checkboxes return 'on' or are absent)
            slack_integration.surveys_enabled = request.POST.get("surveys_enabled") == "on"
            slack_integration.leaderboard_enabled = request.POST.get("leaderboard_enabled") == "on"
            slack_integration.reveals_enabled = request.POST.get("reveals_enabled") == "on"

            # Update schedule
            if request.POST.get("leaderboard_day"):
                slack_integration.leaderboard_day = int(request.POST.get("leaderboard_day"))
            if request.POST.get("leaderboard_time"):
                time_str = request.POST.get("leaderboard_time")
                try:
                    hours, minutes = map(int, time_str.split(":"))
                    slack_integration.leaderboard_time = time(hours, minutes)
                except (ValueError, AttributeError):
                    pass  # Keep existing value on parse error

            # Update channel
            if request.POST.get("leaderboard_channel_id"):
                slack_integration.leaderboard_channel_id = request.POST.get("leaderboard_channel_id")

            slack_integration.save()

            track_event(
                request.user,
                "slack_configured",
                {
                    "team_slug": team.slug,
                    "surveys_enabled": slack_integration.surveys_enabled,
                    "leaderboard_enabled": slack_integration.leaderboard_enabled,
                    "reveals_enabled": slack_integration.reveals_enabled,
                },
            )
        else:
            # Track skip (Slack connection tracking would go in the OAuth callback)
            track_event(
                request.user,
                "onboarding_skipped",
                {"step": "slack", "team_slug": team.slug},
            )
        return redirect("onboarding:complete")

    return render(
        request,
        "onboarding/connect_slack.html",
        {
            "team": team,
            "page_title": _("Connect Slack"),
            "step": 4,
            "sync_task_id": request.session.get("sync_task_id"),
            "jira_sync_task_id": request.session.get("jira_sync_task_id"),
            "slack_integration": slack_integration,
            **_get_onboarding_flags_context(request),
        },
    )
