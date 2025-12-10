import json

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from health_check.views import MainView

from apps.integrations.models import TrackedRepository
from apps.integrations.services.github_webhooks import validate_webhook_signature
from apps.metrics import processors
from apps.teams.decorators import login_and_team_required
from apps.teams.helpers import get_open_invitations_for_user


def home(request):
    if request.user.is_authenticated:
        team = request.default_team
        if team:
            return HttpResponseRedirect(reverse("web_team:home", args=[team.slug]))
        else:
            if (open_invitations := get_open_invitations_for_user(request.user)) and len(open_invitations) > 1:
                invitation = open_invitations[0]
                return HttpResponseRedirect(reverse("teams:accept_invitation", args=[invitation["id"]]))

            messages.info(
                request,
                _("Teams are enabled but you have no teams. Create a team below to access the rest of the dashboard."),
            )
            return HttpResponseRedirect(reverse("teams:manage_teams"))
    else:
        return render(request, "web/landing_page.html")


@login_and_team_required
def team_home(request, team_slug):
    assert request.team.slug == team_slug
    return render(
        request,
        "web/app_home.html",
        context={
            "team": request.team,
            "active_tab": "dashboard",
            "page_title": _("{team} Dashboard").format(team=request.team),
        },
    )


def simulate_error(request):
    raise Exception("This is a simulated error.")


class HealthCheck(MainView):
    def get(self, request, *args, **kwargs):
        tokens = settings.HEALTH_CHECK_TOKENS
        if tokens and request.GET.get("token") not in tokens:
            raise Http404
        return super().get(request, *args, **kwargs)


@csrf_exempt
def github_webhook(request):
    """Handle GitHub webhook events.

    Validates the webhook signature and processes events from tracked repositories.
    """
    # Only accept POST requests
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # Check for signature header
    signature_header = request.META.get("HTTP_X_HUB_SIGNATURE_256")
    if not signature_header:
        return JsonResponse({"error": "Missing signature header"}, status=401)

    # Parse the payload
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    # Extract repository ID from payload
    repository = payload.get("repository", {})
    github_repo_id = repository.get("id")

    if not github_repo_id:
        return JsonResponse({"error": "Missing repository ID in payload"}, status=400)

    # Look up the tracked repository
    try:
        tracked_repo = TrackedRepository.objects.select_related("integration").get(github_repo_id=github_repo_id)
    except TrackedRepository.DoesNotExist:
        return JsonResponse({"error": "Repository not tracked"}, status=404)

    # Validate the webhook signature
    webhook_secret = tracked_repo.integration.webhook_secret
    if not validate_webhook_signature(request.body, signature_header, webhook_secret):
        return JsonResponse({"error": "Invalid signature"}, status=401)

    # Extract event type from header
    event_type = request.META.get("HTTP_X_GITHUB_EVENT", "unknown")
    team = tracked_repo.integration.team

    # Dispatch to appropriate handler based on event type
    if event_type == "pull_request":
        processors.handle_pull_request_event(team, payload)
    elif event_type == "pull_request_review":
        processors.handle_pull_request_review_event(team, payload)

    # Return success response with event and team_id
    return JsonResponse(
        {
            "event": event_type,
            "team_id": team.id,
        },
        status=200,
    )
