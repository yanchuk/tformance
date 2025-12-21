"""
Views for the insights API.

Provides endpoints for LLM-powered insight summaries and Q&A.
"""

import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from apps.insights.services.qa import answer_question, get_suggested_questions
from apps.insights.services.summarizer import summarize_daily_insights
from apps.teams.decorators import login_and_team_required

logger = logging.getLogger(__name__)


@login_and_team_required
@require_GET
@ratelimit(key="user", rate="10/m", method="GET", block=True)
def get_summary(request):
    """Get AI-generated summary of today's insights.

    Returns a 2-3 sentence summary of the team's daily insights.
    Results are cached for 1 hour.

    Args:
        request: The HTTP request.

    Returns:
        JsonResponse with the summary text.
    """
    skip_cache = request.GET.get("refresh") == "true"

    try:
        summary = summarize_daily_insights(
            team=request.team,
            skip_cache=skip_cache,
        )
        return JsonResponse({"summary": summary})
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return JsonResponse(
            {"error": "Failed to generate summary. Please try again later."},
            status=500,
        )


@login_and_team_required
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def ask_question(request):
    """Ask a natural language question about team metrics.

    Uses Gemini with function calling to answer questions about
    team metrics and performance.

    Args:
        request: The HTTP request with JSON body containing "question".

    Returns:
        JsonResponse with the answer text.
    """
    try:
        data = json.loads(request.body)
        question = data.get("question", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    if not question:
        return JsonResponse({"error": "Question is required"}, status=400)

    if len(question) > 500:
        return JsonResponse(
            {"error": "Question is too long (max 500 characters)"},
            status=400,
        )

    try:
        answer = answer_question(
            team=request.team,
            question=question,
            user_id=str(request.user.id),
        )
        return JsonResponse({"answer": answer})
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        return JsonResponse(
            {"error": "Failed to answer question. Please try again later."},
            status=500,
        )


@login_and_team_required
@require_GET
def suggested_questions(request):
    """Get a list of suggested questions.

    Returns example questions users can ask to get started.

    Args:
        request: The HTTP request.

    Returns:
        JsonResponse with a list of suggested questions.
    """
    return JsonResponse({"questions": get_suggested_questions()})
