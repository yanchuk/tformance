"""
Views for the AI feedback app.
"""

import json

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.feedback.forms import FeedbackForm
from apps.feedback.models import CONTENT_TYPE_CHOICES, AIFeedback, LLMFeedback
from apps.metrics.models import TeamMember
from apps.teams.decorators import login_and_team_required
from apps.utils.analytics import track_event


def _is_htmx(request):
    """Check if request is from HTMX."""
    return request.headers.get("HX-Request") == "true"


def _get_current_member(request):
    """Get the TeamMember for the current user if one exists."""
    try:
        return TeamMember.objects.get(
            team=request.team,
            email=request.user.email,
        )
    except TeamMember.DoesNotExist:
        return None


@login_and_team_required
@require_GET
def dashboard(request):
    """Display the feedback dashboard."""
    feedback_list = AIFeedback.for_team.all()

    # Filtering
    category = request.GET.get("category")
    status = request.GET.get("status")

    if category:
        feedback_list = feedback_list.filter(category=category)
    if status:
        feedback_list = feedback_list.filter(status=status)

    # Stats
    total_count = AIFeedback.for_team.count()
    open_count = AIFeedback.for_team.filter(status="open").count()
    resolved_count = AIFeedback.for_team.filter(status="resolved").count()

    context = {
        "feedback_list": feedback_list[:50],  # Limit for performance
        "total_count": total_count,
        "open_count": open_count,
        "resolved_count": resolved_count,
        "selected_category": category,
        "selected_status": status,
    }

    return render(request, "feedback/dashboard.html", context)


@login_and_team_required
def create_feedback(request):
    """Create new feedback or show the form."""
    # GET request - show the form (for HTMX modal)
    if request.method == "GET":
        initial = {}
        pr_id = request.GET.get("pr")
        if pr_id:
            from apps.metrics.models import PullRequest

            try:
                pr = PullRequest.for_team.get(pk=pr_id)
                initial["pull_request"] = pr
            except PullRequest.DoesNotExist:
                pass
        form = FeedbackForm(initial=initial)
        return render(
            request,
            "feedback/partials/feedback_form.html",
            {"form": form},
        )

    # POST request - process the form
    form = FeedbackForm(request.POST)

    if form.is_valid():
        feedback = form.save(commit=False)
        feedback.team = request.team
        feedback.reported_by = _get_current_member(request)
        feedback.save()

        # Track feedback submission
        track_event(
            request.user,
            "feedback_submitted",
            {
                "team_slug": request.team.slug,
                "category": feedback.category,
                "has_text": bool(feedback.description),
            },
        )

        if _is_htmx(request):
            return render(
                request,
                "feedback/partials/feedback_success.html",
                {"feedback": feedback},
            )
        return redirect("feedback:dashboard")

    # Form has errors
    if _is_htmx(request):
        return render(
            request,
            "feedback/partials/feedback_form.html",
            {"form": form},
            status=200,  # HTMX expects 200 even for form errors
        )
    return render(request, "feedback/create.html", {"form": form})


@login_and_team_required
@require_GET
def feedback_detail(request, pk):
    """View feedback detail."""
    try:
        feedback = AIFeedback.for_team.get(pk=pk)
    except AIFeedback.DoesNotExist as err:
        raise Http404("Feedback not found") from err

    return render(request, "feedback/detail.html", {"feedback": feedback})


@login_and_team_required
@require_POST
def resolve_feedback(request, pk):
    """Mark feedback as resolved."""
    try:
        feedback = AIFeedback.for_team.get(pk=pk)
    except AIFeedback.DoesNotExist as err:
        raise Http404("Feedback not found") from err

    feedback.status = "resolved"
    feedback.resolved_at = timezone.now()
    feedback.save()

    if _is_htmx(request):
        return render(
            request,
            "feedback/partials/feedback_card.html",
            {"feedback": feedback},
        )
    return redirect("feedback:dashboard")


@login_and_team_required
@require_GET
def cto_summary(request):
    """Render the CTO dashboard summary card for AI feedback."""
    open_count = AIFeedback.for_team.filter(status="open").count()
    resolved_count = AIFeedback.for_team.filter(status="resolved").count()
    recent_feedback = AIFeedback.for_team.order_by("-created_at")[:5]

    return render(
        request,
        "feedback/partials/cto_summary_card.html",
        {
            "open_count": open_count,
            "resolved_count": resolved_count,
            "recent_feedback": recent_feedback,
        },
    )


# =============================================================================
# LLM Feedback Views
# =============================================================================


def _get_valid_content_types():
    """Return a set of valid content type choices."""
    return {choice[0] for choice in CONTENT_TYPE_CHOICES}


@login_and_team_required
@require_POST
def submit_llm_feedback(request):
    """Submit feedback for LLM-generated content."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    content_type = data.get("content_type")
    content_id = data.get("content_id")
    rating = data.get("rating")
    content_snapshot = data.get("content_snapshot", {})
    input_context = data.get("input_context")
    prompt_version = data.get("prompt_version", "")

    # Validate content_type
    if content_type not in _get_valid_content_types():
        return JsonResponse({"error": "Invalid content_type"}, status=400)

    # Create or update feedback (unique on: team, user, content_type, content_id)
    feedback, created = LLMFeedback.objects.update_or_create(
        team=request.team,
        user=request.user,
        content_type=content_type,
        content_id=content_id,
        defaults={
            "rating": rating,
            "content_snapshot": content_snapshot,
            "input_context": input_context,
            "prompt_version": prompt_version,
        },
    )

    # Track analytics event
    track_event(
        request.user,
        "llm_feedback_submitted",
        {
            "content_type": content_type,
            "rating": "positive" if rating else "negative",
            "is_new": created,
            "has_snapshot": bool(content_snapshot),
            "prompt_version": prompt_version or None,
        },
    )

    return JsonResponse({"id": feedback.id})


@login_and_team_required
@require_GET
def get_llm_feedback(request, content_type, content_id):
    """Get existing LLM feedback for specific content."""
    try:
        feedback = LLMFeedback.objects.get(
            team=request.team,
            user=request.user,
            content_type=content_type,
            content_id=content_id,
        )
        return JsonResponse(
            {
                "id": feedback.id,
                "rating": feedback.rating,
                "comment": feedback.comment or "",
            }
        )
    except LLMFeedback.DoesNotExist:
        return JsonResponse({"rating": None})


@login_and_team_required
@require_POST
def add_llm_feedback_comment(request, pk):
    """Add a comment to existing LLM feedback."""
    try:
        feedback = LLMFeedback.objects.get(
            pk=pk,
            team=request.team,
            user=request.user,
        )
    except LLMFeedback.DoesNotExist as err:
        raise Http404("Feedback not found") from err

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    comment = data.get("comment", "")
    feedback.comment = comment
    feedback.save()

    # Track analytics event
    track_event(
        request.user,
        "llm_feedback_comment_added",
        {
            "content_type": feedback.content_type,
            "rating": "positive" if feedback.rating else "negative",
            "comment_length": len(comment),
        },
    )

    return JsonResponse({"success": True})
