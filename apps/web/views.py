import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import (
    Http404,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
from health_check.views import MainView

from apps.integrations.models import TrackedRepository
from apps.integrations.services.github_webhooks import validate_webhook_signature
from apps.integrations.services.status import get_team_integration_status, get_team_sync_status
from apps.metrics import processors
from apps.metrics.models import PRSurveyReview, TeamMember
from apps.metrics.services.quick_stats import get_team_quick_stats
from apps.metrics.services.survey_service import record_author_response, record_reviewer_response
from apps.teams.decorators import login_and_team_required
from apps.teams.helpers import get_open_invitations_for_user
from apps.web.decorators import (
    require_survey_author_access,
    require_survey_reviewer_access,
    require_valid_survey_token,
)

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
            # If onboarding not complete, redirect to continue onboarding
            if not team.onboarding_complete:
                return HttpResponseRedirect(reverse("onboarding:select_repos"))
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


def ai_impact_report(request):
    """Serve the AI Impact Report from public_report/index.html."""
    import os

    from django.http import FileResponse, HttpResponse

    report_path = os.path.join(settings.BASE_DIR, "public_report", "index.html")

    if os.path.exists(report_path):
        return FileResponse(open(report_path, "rb"), content_type="text/html")
    else:
        return HttpResponse("Report not found", status=404)


@login_and_team_required
def team_home(request):
    """Team home page with conditional content based on integration status.

    Shows setup wizard for new users (no integrations) or quick stats
    and recent activity for users with data.
    """
    team = request.team
    integration_status = get_team_integration_status(team)
    sync_status = get_team_sync_status(team)

    context = {
        "team": team,
        "active_tab": "dashboard",
        "page_title": _("{team} Dashboard").format(team=team),
        "integration_status": integration_status,
        **sync_status,  # Unpacks sync_in_progress, sync_progress_percent, repos_syncing, repos_total, repos_synced
    }

    # Only fetch quick stats if the team has data
    if integration_status["has_data"]:
        context["quick_stats"] = get_team_quick_stats(team, days=7)

    return render(request, "web/app_home.html", context)


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
        tracked_repo = TrackedRepository.objects.select_related("integration").get(github_repo_id=github_repo_id)  # noqa: TEAM001 - Webhook lookup, validated after
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


# Survey Views (token-based access)


@login_required
@require_valid_survey_token()
def survey_landing(request, token):
    """Landing page for survey - redirects to author or reviewer form based on user."""
    # For now, just redirect to author form (minimal implementation)
    # In full implementation, would check if user is author or reviewer
    return HttpResponseRedirect(reverse("web:survey_author", kwargs={"token": token}))


@login_required
@require_valid_survey_token()
@require_survey_author_access
def survey_author(request, token):
    """Show author survey form (AI assistance question).

    Supports one-click voting via ?vote=yes or ?vote=no query parameter.
    If vote param is present and valid, records the vote and redirects to complete page.
    """
    survey = request.survey

    # Check for one-click vote from PR description link
    vote = request.GET.get("vote")
    if vote in ("yes", "no"):
        # Only process if author hasn't already responded
        if survey.author_ai_assisted is None:
            ai_assisted = vote == "yes"
            record_author_response(survey, ai_assisted, response_source="github")
            logger.info(f"One-click author vote recorded for survey {survey.id}: ai_assisted={ai_assisted}")
        return HttpResponseRedirect(reverse("web:survey_complete", kwargs={"token": token}))

    return render(request, "web/surveys/author.html", {"survey": survey, "token": token})


@login_required
@require_valid_survey_token()
@require_survey_reviewer_access
def survey_reviewer(request, token):
    """Show reviewer survey form (quality + AI guess).

    Supports one-click voting via ?vote=1, ?vote=2, or ?vote=3 query parameter.
    If vote param is present and valid, records the quality vote and redirects to complete page.
    """
    from apps.metrics.services.survey_service import record_reviewer_quality_vote
    from apps.web.decorators import get_user_github_id

    survey = request.survey

    # Get the current user's TeamMember
    github_id = get_user_github_id(request.user)
    reviewer = None
    if github_id:
        reviewer = TeamMember.objects.filter(team=survey.team, github_id=github_id).first()

    # Check for one-click vote from PR description link
    vote = request.GET.get("vote")
    if vote in ("1", "2", "3") and reviewer:
        quality = int(vote)
        # Get or create PRSurveyReview for this reviewer
        survey_review, created = PRSurveyReview.objects.get_or_create(
            survey=survey, reviewer=reviewer, defaults={"team": survey.team}
        )
        # Only process if reviewer hasn't already responded
        if survey_review.responded_at is None:
            record_reviewer_quality_vote(survey_review, quality, response_source="github")
            logger.info(
                f"One-click reviewer vote recorded for survey {survey.id}: reviewer={reviewer.id}, quality={quality}"
            )
        return HttpResponseRedirect(reverse("web:survey_complete", kwargs={"token": token}))

    return render(
        request,
        "web/surveys/reviewer.html",
        {"survey": survey, "token": token, "reviewer": reviewer},
    )


def _is_author_submission(post_data):
    """Check if POST data represents an author survey submission."""
    return "ai_assisted" in post_data and "quality_rating" not in post_data


def _is_reviewer_submission(post_data):
    """Check if POST data represents a reviewer survey submission."""
    return "quality_rating" in post_data and "ai_guess" in post_data


def _handle_author_submission(survey, post_data):
    """Process author survey submission."""
    if survey.author_ai_assisted is not None:
        logger.info(f"Author already responded to survey {survey.id}, skipping duplicate submission")
        return

    ai_assisted = post_data.get("ai_assisted") == "true"
    record_author_response(survey, ai_assisted)
    logger.info(f"Author response recorded for survey {survey.id}: ai_assisted={ai_assisted}")


def _handle_reviewer_submission(survey, post_data):
    """Process reviewer survey submission.

    Returns:
        dict or None: Reveal data if author has responded, None otherwise.
        Reveal data contains: guess_correct, was_ai, accuracy
    """
    from apps.metrics.services.survey_service import get_reviewer_accuracy_stats

    # Validate required fields
    quality_rating_str = post_data.get("quality_rating")
    ai_guess_str = post_data.get("ai_guess")
    reviewer_id = post_data.get("reviewer_id")

    if not all([quality_rating_str, ai_guess_str, reviewer_id]):
        logger.warning(f"Reviewer submission missing required fields for survey {survey.id}")
        return None

    # Parse and validate quality rating
    try:
        quality_rating = int(quality_rating_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid quality_rating for survey {survey.id}: {quality_rating_str}")
        return None

    ai_guess = ai_guess_str == "true"

    # Get the reviewer TeamMember
    try:
        reviewer = TeamMember.objects.get(id=reviewer_id, team=survey.team)
    except TeamMember.DoesNotExist:
        logger.warning(f"Invalid reviewer_id {reviewer_id} for survey {survey.id}")
        return None

    # Get or create PRSurveyReview for this reviewer
    survey_review, created = PRSurveyReview.objects.get_or_create(
        survey=survey, reviewer=reviewer, defaults={"team": survey.team}
    )

    # Record the response (only if not already responded)
    if survey_review.responded_at is not None:
        logger.info(f"Reviewer {reviewer.id} already responded to survey {survey.id}, skipping duplicate")
        return None

    record_reviewer_response(survey_review, quality_rating, ai_guess)
    logger.info(
        f"Reviewer response recorded for survey {survey.id}: "
        f"reviewer={reviewer.id}, quality_rating={quality_rating}, ai_guess={ai_guess}"
    )

    # Build reveal data if author has responded
    if survey.author_ai_assisted is not None:
        # Refresh survey_review to get updated guess_correct
        survey_review.refresh_from_db()
        accuracy_stats = get_reviewer_accuracy_stats(reviewer)
        return {
            "guess_correct": survey_review.guess_correct,
            "was_ai": survey.author_ai_assisted,
            "accuracy": accuracy_stats,
        }

    return None


@login_required
@require_valid_survey_token()
def survey_submit(request, token):
    """Handle survey form submission."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    survey = request.survey
    reveal_data = None
    is_reviewer = False

    # Determine submission type and handle accordingly
    if _is_author_submission(request.POST):
        _handle_author_submission(survey, request.POST)
    elif _is_reviewer_submission(request.POST):
        is_reviewer = True
        reveal_data = _handle_reviewer_submission(survey, request.POST)
    else:
        logger.warning(f"Unknown submission type for survey {survey.id}")

    # Store reveal data in session for the complete page
    if reveal_data:
        request.session["survey_reveal"] = reveal_data
        request.session["survey_reveal_token"] = token
    request.session["is_reviewer_submission"] = is_reviewer

    return HttpResponseRedirect(reverse("web:survey_complete", kwargs={"token": token}))


@login_required
@require_valid_survey_token(allow_expired=True)
def survey_complete(request, token):
    """Show thank you message after survey completion."""
    # Get reveal data from session (only if it matches this survey token)
    reveal = None
    is_reviewer_submission = request.session.pop("is_reviewer_submission", False)

    if request.session.get("survey_reveal_token") == token:
        reveal = request.session.pop("survey_reveal", None)
        request.session.pop("survey_reveal_token", None)

    return render(
        request,
        "web/surveys/complete.html",
        {
            "survey": request.survey,
            "token": token,
            "reveal": reveal,
            "is_reviewer_submission": is_reviewer_submission,
        },
    )
