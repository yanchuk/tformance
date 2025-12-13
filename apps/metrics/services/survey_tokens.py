"""Survey Token Generation Service - Generate secure tokens for survey URLs.

This module provides cryptographically secure token generation for PRSurvey models.
Tokens are URL-safe and unique, with configurable expiry dates.
"""

import logging
import secrets
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from apps.metrics.models import PRSurvey

logger = logging.getLogger(__name__)


class SurveyTokenError(Exception):
    """Base exception for all survey token-related errors."""

    pass


class InvalidTokenError(SurveyTokenError):
    """Raised when a survey token is invalid or not found."""

    pass


class ExpiredTokenError(SurveyTokenError):
    """Raised when a survey token has expired."""

    pass


def generate_survey_token() -> str:
    """Generate a cryptographically secure, URL-safe token.

    Returns:
        A 43-character URL-safe string (32 bytes base64url encoded)
    """
    return secrets.token_urlsafe(32)


def set_survey_token(survey: "PRSurvey", expiry_days: int = 7) -> "PRSurvey":
    """Set a secure token and expiry date on a PRSurvey.

    Args:
        survey: PRSurvey instance to set token on
        expiry_days: Number of days until token expires (default: 7)

    Side effects:
        - Sets survey.token to a new unique token
        - Sets survey.token_expires_at to expiry_days from now
        - Saves the survey to the database

    Returns:
        The updated survey instance
    """
    survey.token = generate_survey_token()
    survey.token_expires_at = timezone.now() + timedelta(days=expiry_days)
    survey.save()
    return survey


def validate_survey_token(token: str) -> "PRSurvey":
    """Validate a survey token and return the associated survey.

    Args:
        token: The survey token to validate

    Returns:
        PRSurvey: The survey associated with the token

    Raises:
        InvalidTokenError: If token is None, empty, or not found
        ExpiredTokenError: If the token has expired
    """
    from apps.metrics.models import PRSurvey

    if not token:
        logger.warning("Token validation failed: empty or None token")
        raise InvalidTokenError("Token is required")

    try:
        survey = PRSurvey.objects.get(token=token)  # noqa: TEAM001 - Token-based lookup (cryptographically secure)
    except PRSurvey.DoesNotExist:
        logger.warning("Token validation failed: token not found", extra={"token": token[:8] + "..."})
        raise InvalidTokenError("Invalid token")

    if survey.is_token_expired():
        logger.info(
            "Token validation failed: token expired",
            extra={"survey_id": survey.id, "expires_at": survey.token_expires_at},
        )
        raise ExpiredTokenError("Token has expired")

    logger.debug("Token validated successfully", extra={"survey_id": survey.id})
    return survey
