"""Slack interactions webhook handler.

Handles button clicks from Slack surveys (author and reviewer responses).
"""

import json
import logging
from urllib.parse import parse_qs

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
from slack_sdk.signature import SignatureVerifier

# Slack webhook rate limit: 100 requests per minute per IP
SLACK_WEBHOOK_RATE_LIMIT = "100/m"

# Maximum webhook payload size: 1 MB (Slack payloads are typically small)
MAX_SLACK_PAYLOAD_SIZE = 1 * 1024 * 1024  # 1 MB in bytes

from apps.integrations.services.slack_surveys import (
    ACTION_AI_GUESS_NO,
    ACTION_AI_GUESS_YES,
    ACTION_AUTHOR_AI_NO,
    ACTION_AUTHOR_AI_YES,
    ACTION_QUALITY_1,
    ACTION_QUALITY_2,
    ACTION_QUALITY_3,
)
from apps.metrics.models import PRSurvey, PRSurveyReview
from apps.metrics.services.survey_service import record_author_response, record_reviewer_response

logger = logging.getLogger(__name__)

# Map quality action IDs to rating values
QUALITY_ACTION_MAP = {
    ACTION_QUALITY_1: 1,
    ACTION_QUALITY_2: 2,
    ACTION_QUALITY_3: 3,
}


def verify_slack_signature(request) -> bool:
    """Verify Slack request signature.

    Args:
        request: Django request object

    Returns:
        True if signature is valid, False otherwise
    """
    if not settings.SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET not configured")
        return False

    verifier = SignatureVerifier(signing_secret=settings.SLACK_SIGNING_SECRET)

    try:
        return verifier.is_valid_request(
            body=request.body.decode("utf-8"),
            headers={
                "X-Slack-Request-Timestamp": request.headers.get("X-Slack-Request-Timestamp", ""),
                "X-Slack-Signature": request.headers.get("X-Slack-Signature", ""),
            },
        )
    except Exception as e:
        logger.warning(f"Slack signature verification failed: {e}")
        return False


def parse_slack_payload(request) -> dict:
    """Parse Slack interaction payload from request.

    Args:
        request: Django request object

    Returns:
        Parsed payload dict
    """
    body = request.body.decode("utf-8")
    parsed = parse_qs(body)
    payload_str = parsed.get("payload", ["{}"])[0]
    return json.loads(payload_str)


def handle_author_response(survey_id: str, ai_assisted: bool) -> None:
    """Handle author response to AI-assisted question.

    Args:
        survey_id: PRSurvey ID
        ai_assisted: Whether PR was AI-assisted
    """
    try:
        survey = PRSurvey.objects.get(id=int(survey_id))

        # Ignore if already responded
        if survey.author_ai_assisted is not None:
            logger.info(f"Survey {survey_id} already has author response, ignoring")
            return

        record_author_response(survey, ai_assisted)
        logger.info(f"Recorded author response for survey {survey_id}: ai_assisted={ai_assisted}")

    except PRSurvey.DoesNotExist:
        logger.warning(f"Survey {survey_id} not found")
    except Exception as e:
        logger.error(f"Error handling author response for survey {survey_id}: {e}")


def handle_reviewer_response(payload: dict) -> None:
    """Handle reviewer response to quality and AI guess questions.

    Args:
        payload: Full Slack interaction payload
    """
    # Extract quality rating and AI guess from actions
    quality_rating = None
    ai_guess = None
    survey_review_id = None

    for action in payload.get("actions", []):
        action_id = action.get("action_id")
        value = action.get("value")

        # Check if it's a quality rating action
        if action_id in QUALITY_ACTION_MAP:
            quality_rating = QUALITY_ACTION_MAP[action_id]
            survey_review_id = value
        elif action_id == ACTION_AI_GUESS_YES:
            ai_guess = True
            if survey_review_id is None:
                survey_review_id = value
        elif action_id == ACTION_AI_GUESS_NO:
            ai_guess = False
            if survey_review_id is None:
                survey_review_id = value

    # Must have both quality and AI guess
    if quality_rating is None or ai_guess is None:
        logger.warning("Incomplete reviewer response (missing quality or ai_guess)")
        return

    if survey_review_id is None:
        logger.warning("No survey_review_id found in reviewer response")
        return

    try:
        survey_review = PRSurveyReview.objects.get(id=int(survey_review_id))

        # Ignore if already responded
        if survey_review.quality_rating is not None:
            logger.info(f"Survey review {survey_review_id} already has response, ignoring")
            return

        record_reviewer_response(survey_review, quality_rating, ai_guess)
        logger.info(
            f"Recorded reviewer response for survey review {survey_review_id}: "
            f"quality={quality_rating}, ai_guess={ai_guess}"
        )

    except PRSurveyReview.DoesNotExist:
        logger.warning(f"Survey review {survey_review_id} not found")
    except Exception as e:
        logger.error(f"Error handling reviewer response for survey review {survey_review_id}: {e}")


# SECURITY: @csrf_exempt justified - External webhook endpoint receiving requests from Slack servers.
# Cannot use CSRF tokens. Alternative authentication: Slack signature validation using
# X-Slack-Signature header with shared signing secret (HMAC-SHA256). Additional protections:
# - Rate limiting: 100 requests/min per IP (django-ratelimit)
# - Timestamp validation (built into SignatureVerifier, prevents replay attacks)
# - POST-only method enforcement
@csrf_exempt
@ratelimit(key="ip", rate=SLACK_WEBHOOK_RATE_LIMIT, method="POST", block=True)
def slack_interactions(request):
    """Handle Slack interaction payloads (button clicks).

    1. Verify Slack signature
    2. Parse payload
    3. Route to appropriate handler
    4. Return 200 acknowledgment

    Rate limited to 100 requests per minute per IP.

    Security Controls:
        - Slack signature validation (X-Slack-Signature header)
        - Timestamp validation (X-Slack-Request-Timestamp, prevents replay)
        - Rate limiting: 100/min per IP
        - POST-only method enforcement
        - Payload size limit: 1 MB max

    Args:
        request: Django request object

    Returns:
        HttpResponse (200 on success, 403 on invalid signature, 405 on wrong method, 413 on payload too large)
    """
    if request.method != "POST":
        return HttpResponse(status=405)

    # Check payload size to prevent DoS via large payloads
    content_length = request.META.get("CONTENT_LENGTH")
    if content_length:
        try:
            if int(content_length) > MAX_SLACK_PAYLOAD_SIZE:
                logger.warning(f"Slack webhook payload too large: {content_length} bytes")
                return JsonResponse({"error": "Payload too large"}, status=413)
        except (ValueError, TypeError):
            pass  # Invalid content-length header, let Django handle it

    # Verify signature
    if not verify_slack_signature(request):
        return HttpResponseForbidden("Invalid signature")

    # Parse payload
    payload = parse_slack_payload(request)

    # Route by action_id
    for action in payload.get("actions", []):
        action_id = action.get("action_id")
        value = action.get("value")

        if action_id in (ACTION_AUTHOR_AI_YES, ACTION_AUTHOR_AI_NO):
            handle_author_response(value, action_id == ACTION_AUTHOR_AI_YES)
        elif action_id in (
            ACTION_QUALITY_1,
            ACTION_QUALITY_2,
            ACTION_QUALITY_3,
            ACTION_AI_GUESS_YES,
            ACTION_AI_GUESS_NO,
        ):
            # Reviewer response - quality and AI guess come together
            handle_reviewer_response(payload)
            break  # Only process once per payload

    return HttpResponse(status=200)
