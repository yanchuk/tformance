"""Copilot-related onboarding views.

Contains views for optional Copilot connection during onboarding.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from apps.integrations.services.copilot_activation import activate_copilot_for_team
from apps.integrations.services.integration_flags import get_next_onboarding_step, is_integration_enabled
from apps.utils.analytics import track_event

from ._helpers import _get_onboarding_flags_context

logger = logging.getLogger(__name__)


@login_required
def connect_copilot(request):
    """Optional step to connect GitHub Copilot.

    GET: Show the Copilot connection page with benefits
    POST with action=connect: Activate Copilot and redirect to next step
    POST with action=skip: Skip Copilot and continue to next step

    If the integration_copilot_enabled flag is off, automatically skip to the next step.
    """
    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Check if Copilot integration is enabled via feature flag
    if not is_integration_enabled(request, "copilot"):
        # Skip to next step - map slug to URL name
        slug_to_url = {"jira": "connect_jira", "slack": "connect_slack", "complete": "complete"}
        next_step = get_next_onboarding_step(request, "copilot")
        url_name = slug_to_url.get(next_step, "complete")
        return redirect(f"onboarding:{url_name}")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "connect":
            # Activate Copilot for this team
            result = activate_copilot_for_team(team)
            logger.info(f"Copilot activation result for team {team.name}: {result}")

            # Track event
            track_event(
                request.user,
                "copilot_connected",
                {"team_slug": team.slug, "result": result.get("status")},
            )

            # Redirect to next step - map slug to URL name
            slug_to_url = {"jira": "connect_jira", "slack": "connect_slack", "complete": "complete"}
            next_step = get_next_onboarding_step(request, "copilot")
            url_name = slug_to_url.get(next_step, "complete")
            return redirect(f"onboarding:{url_name}")

        elif action == "skip":
            # Track skip event
            track_event(
                request.user,
                "onboarding_skipped",
                {"step": "copilot", "team_slug": team.slug},
            )

            # Redirect to next step - map slug to URL name
            slug_to_url = {"jira": "connect_jira", "slack": "connect_slack", "complete": "complete"}
            next_step = get_next_onboarding_step(request, "copilot")
            url_name = slug_to_url.get(next_step, "complete")
            return redirect(f"onboarding:{url_name}")

    return render(
        request,
        "onboarding/copilot.html",
        {
            "team": team,
            "page_title": _("Connect GitHub Copilot"),
            "step": 4,  # After sync_progress
            "sync_task_id": request.session.get("sync_task_id"),
            **_get_onboarding_flags_context(request),
        },
    )
