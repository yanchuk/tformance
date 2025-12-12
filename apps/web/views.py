import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
from health_check.views import MainView

from apps.integrations.models import TrackedRepository
from apps.integrations.services.github_webhooks import validate_webhook_signature
from apps.metrics import processors
from apps.teams.decorators import login_and_team_required
from apps.teams.helpers import get_open_invitations_for_user

logger = logging.getLogger(__name__)

# Webhook replay protection: cache timeout in seconds (1 hour)
WEBHOOK_REPLAY_CACHE_TIMEOUT = 3600

# Webhook rate limit: 100 requests per minute per IP
WEBHOOK_RATE_LIMIT = "100/m"

# Maximum webhook payload size: 5 MB (GitHub allows up to 25 MB, but we limit for safety)
MAX_WEBHOOK_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5 MB in bytes


def home(request):
    if request.user.is_authenticated:
        team = request.default_team
        if team:
            return HttpResponseRedirect(reverse("web_team:home"))
        else:
            # Check for open invitations first
            if open_invitations := get_open_invitations_for_user(request.user):
                invitation = open_invitations[0]
                return HttpResponseRedirect(reverse("teams:accept_invitation", args=[invitation["id"]]))

            # No team and no invitations - redirect to onboarding
            return HttpResponseRedirect(reverse("onboarding:start"))
    else:
        return render(request, "web/landing_page.html")


@login_and_team_required
def team_home(request):
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


# SECURITY: @csrf_exempt justified - External webhook endpoint receiving requests from GitHub servers.
# Cannot use CSRF tokens. Alternative authentication: HMAC-SHA256 signature validation using
# X-Hub-Signature-256 header with shared webhook secret. Additional protections:
# - Rate limiting: 100 requests/min per IP (django-ratelimit)
# - Replay protection: Delivery ID caching with 1-hour TTL
# - Signature timing-safe comparison via hmac.compare_digest()
@csrf_exempt
@ratelimit(key="ip", rate=WEBHOOK_RATE_LIMIT, method="POST", block=True)
def github_webhook(request):
    """Handle GitHub webhook events.

    Validates the webhook signature and processes events from tracked repositories.
    Includes replay protection using the X-GitHub-Delivery header.
    Rate limited to 100 requests per minute per IP.

    Security Controls:
        - HMAC-SHA256 signature validation (X-Hub-Signature-256)
        - Replay protection via X-GitHub-Delivery header caching
        - Rate limiting: 100/min per IP
        - POST-only method enforcement
        - Payload size limit: 5 MB max
    """
    # Only accept POST requests
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # Check payload size to prevent DoS via large payloads
    content_length = request.META.get("CONTENT_LENGTH")
    if content_length:
        try:
            if int(content_length) > MAX_WEBHOOK_PAYLOAD_SIZE:
                logger.warning(f"Webhook payload too large: {content_length} bytes")
                return JsonResponse({"error": "Payload too large"}, status=413)
        except (ValueError, TypeError):
            pass  # Invalid content-length header, let Django handle it

    # Check for signature header
    signature_header = request.META.get("HTTP_X_HUB_SIGNATURE_256")
    if not signature_header:
        return JsonResponse({"error": "Missing signature header"}, status=401)

    # Check for delivery ID (replay protection)
    delivery_id = request.META.get("HTTP_X_GITHUB_DELIVERY")
    if not delivery_id:
        return JsonResponse({"error": "Missing delivery ID"}, status=400)

    # Check if this webhook has already been processed (replay protection)
    cache_key = f"webhook:github:{delivery_id}"
    if cache.get(cache_key):
        logger.warning(f"Duplicate webhook delivery detected: {delivery_id}")
        return JsonResponse({"error": "Duplicate delivery"}, status=409)

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

    # Mark webhook as processed (replay protection)
    cache.set(cache_key, True, WEBHOOK_REPLAY_CACHE_TIMEOUT)

    # Return minimal success response (avoid leaking internal IDs)
    return JsonResponse(
        {
            "status": "processed",
            "event": event_type,
        },
        status=200,
    )
