"""
Web app decorators.
"""

import logging
from functools import wraps

from allauth.socialaccount.models import SocialAccount
from django.http import Http404, HttpResponse, HttpResponseForbidden

from apps.metrics.models import PRSurvey
from apps.metrics.services.survey_tokens import ExpiredTokenError, InvalidTokenError, validate_survey_token

logger = logging.getLogger(__name__)


def require_valid_survey_token(allow_expired=False):
    """
    Decorator to validate survey token and attach survey to request.

    Args:
        allow_expired: If True, allows expired tokens if survey exists (useful for completion pages)

    Usage:
        @login_required
        @require_valid_survey_token()
        def my_view(request, token):
            survey = request.survey  # Automatically available
            ...

        @login_required
        @require_valid_survey_token(allow_expired=True)
        def completion_view(request, token):
            survey = request.survey  # Available even if token expired
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, token, *args, **kwargs):
            try:
                survey = validate_survey_token(token)
                request.survey = survey
            except InvalidTokenError:
                raise Http404("Survey not found")
            except ExpiredTokenError:
                if allow_expired:
                    # Allow expired tokens if survey exists (user already completed it)
                    try:
                        survey = PRSurvey.objects.get(token=token)  # noqa: TEAM001 - Token-based lookup
                        request.survey = survey
                    except PRSurvey.DoesNotExist:
                        raise Http404("Survey not found")
                else:
                    return HttpResponse("Survey link has expired", status=410)

            return view_func(request, token, *args, **kwargs)

        return wrapper

    return decorator


def get_user_github_id(user):
    """Get the GitHub ID for a user from their social account."""
    try:
        social = SocialAccount.objects.get(user=user, provider="github")
        return social.uid
    except SocialAccount.DoesNotExist:
        return None


def verify_author_access(user, survey):
    """Verify the user is the PR author. Returns True if authorized."""
    github_id = get_user_github_id(user)
    if not github_id:
        return False
    author = survey.author
    if not author or author.github_id != github_id:
        return False
    return True


def verify_reviewer_access(user, survey):
    """Verify the user is a PR reviewer. Returns True if authorized."""
    github_id = get_user_github_id(user)
    if not github_id:
        return False
    # Check if user is a reviewer of this PR
    reviewer_github_ids = survey.pull_request.reviews.values_list("reviewer__github_id", flat=True).distinct()
    return github_id in reviewer_github_ids


def require_survey_author_access(view_func):
    """
    Decorator to verify user is the PR author for this survey.

    Must be used after @login_required and @require_valid_survey_token()
    Expects request.survey to be set by require_valid_survey_token decorator.

    Usage:
        @login_required
        @require_valid_survey_token()
        @require_survey_author_access
        def author_view(request, token):
            # User is verified as the PR author
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        survey = request.survey
        if not verify_author_access(request.user, survey):
            logger.warning(
                f"Unauthorized author survey access attempt: user={request.user.id}, survey={survey.id}, "
                f"author_github_id={survey.author.github_id if survey.author else None}"
            )
            return HttpResponseForbidden("You are not authorized to access this survey")

        return view_func(request, *args, **kwargs)

    return wrapper


def require_survey_reviewer_access(view_func):
    """
    Decorator to verify user is a PR reviewer for this survey.

    Must be used after @login_required and @require_valid_survey_token()
    Expects request.survey to be set by require_valid_survey_token decorator.

    Usage:
        @login_required
        @require_valid_survey_token()
        @require_survey_reviewer_access
        def reviewer_view(request, token):
            # User is verified as a PR reviewer
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        survey = request.survey
        if not verify_reviewer_access(request.user, survey):
            logger.warning(
                f"Unauthorized reviewer survey access attempt: user={request.user.id}, survey={survey.id}, "
                f"pr={survey.pull_request.id if survey.pull_request else None}"
            )
            return HttpResponseForbidden("You are not authorized to access this survey")

        return view_func(request, *args, **kwargs)

    return wrapper
