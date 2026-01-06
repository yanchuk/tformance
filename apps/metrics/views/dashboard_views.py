import json
from datetime import date

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.integrations.services.integration_flags import is_cicd_enabled
from apps.metrics.models import DailyInsight
from apps.metrics.services import insight_service
from apps.metrics.services.insight_llm import resolve_action_url
from apps.metrics.view_utils import get_date_range_from_request
from apps.teams.decorators import login_and_team_required, team_admin_required


def _get_date_range_context(request: HttpRequest) -> dict[str, int | date]:
    """Extract common date range context from request query parameters.

    Args:
        request: The HTTP request object

    Returns:
        Dictionary containing days, start_date, end_date, and active_tab
    """
    days = int(request.GET.get("days") or 30)
    start_date, end_date = get_date_range_from_request(request)

    return {
        "active_tab": "metrics",
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
    }


@login_and_team_required
def home(request: HttpRequest) -> HttpResponse:
    template = "metrics/metrics_home.html#page-content" if request.htmx else "metrics/metrics_home.html"

    return TemplateResponse(request, template, {"active_tab": "metrics"})


@login_and_team_required
def dashboard_redirect(request: HttpRequest) -> HttpResponse:
    """Redirect to appropriate dashboard based on user role."""
    membership = request.team_membership
    if membership.role == "admin":
        return redirect("metrics:analytics_overview")
    return redirect("metrics:team_dashboard")


@team_admin_required
def cto_overview(request: HttpRequest) -> HttpResponse:
    """CTO Overview Dashboard - Admin only.

    Access is blocked during Phase 1 of onboarding (syncing, llm_processing,
    computing_metrics, computing_insights, failed). Dashboard becomes accessible
    once Phase 1 completes (phase1_complete, background_*, complete).
    """
    # Block dashboard during Phase 1 of onboarding
    if not request.team.dashboard_accessible:
        return redirect("onboarding:sync_progress")

    context = _get_date_range_context(request)
    context["insights"] = insight_service.get_recent_insights(request.team)
    context["cicd_enabled"] = is_cicd_enabled(request)
    # Return partial for HTMX requests (e.g., days filter changes)
    template = "metrics/cto_overview.html#page-content" if request.htmx else "metrics/cto_overview.html"
    return TemplateResponse(request, template, context)


@login_and_team_required
def team_dashboard(request: HttpRequest) -> HttpResponse:
    """Team Dashboard - Redirects to unified dashboard at /app/.

    The old team_dashboard URL (/app/metrics/dashboard/team/) is deprecated.
    All dashboard functionality is now available at /app/ (unified dashboard).
    """
    # Preserve days query parameter in redirect
    days = request.GET.get("days")
    if days:
        return redirect(f"/app/?days={days}")
    return redirect("web_team:home")


@require_POST
@login_and_team_required
def dismiss_insight(request: HttpRequest, insight_id: int) -> HttpResponse:
    """Dismiss an insight (HTMX endpoint)."""
    insight = get_object_or_404(DailyInsight, id=insight_id, team=request.team)
    insight.is_dismissed = True
    insight.dismissed_at = timezone.now()
    insight.save()
    return HttpResponse(status=200)


@login_and_team_required
def engineering_insights(request: HttpRequest) -> HttpResponse:
    """Render LLM-generated engineering insights (HTMX endpoint).

    Query params:
        days: Number of days for the insight period (7, 30, or 90)
    """
    days = int(request.GET.get("days") or 30)

    # Get the most recent cached insight for this days period
    # Uses days as comparison_period (e.g., "7", "30", "90")
    insight_record = (
        DailyInsight.objects.filter(
            team=request.team,
            category="llm_insight",
            comparison_period=str(days),
        )
        .order_by("-date")
        .first()
    )

    context = {
        "days": days,
        "insight": None,
        "error": None,
    }

    if insight_record and insight_record.metric_value:
        # Parse the stored JSON insight
        insight_data = insight_record.metric_value

        # Resolve action URLs - handle both string and object formats
        raw_actions = insight_data.get("actions", [])
        resolved_actions = []
        for a in raw_actions:
            # Legacy format: string → convert to object; otherwise use as-is
            action = {"action_type": a, "label": a.replace("_", " ").title()} if isinstance(a, str) else a
            resolved_actions.append({"label": action.get("label", ""), "url": resolve_action_url(action, days)})

        # Normalize detail to always be a string (LLM sometimes returns array)
        raw_detail = insight_data.get("detail", "")
        detail = "\n".join(raw_detail) if isinstance(raw_detail, list) else raw_detail

        # Extract possible_causes from detail if it contains bullet points
        # LLM prompt puts bullets in detail, but template expects separate possible_causes
        raw_causes = insight_data.get("possible_causes", [])
        if raw_causes:
            # Use provided possible_causes if available
            possible_causes = ([raw_causes] if raw_causes else []) if isinstance(raw_causes, str) else raw_causes
        elif "•" in detail:
            # Extract bullet points from detail into possible_causes
            lines = detail.split("\n")
            possible_causes = [line.lstrip("• ").strip() for line in lines if line.strip().startswith("•")]
            # Remove bullet points from detail (keep any non-bullet content)
            non_bullet_lines = [line for line in lines if not line.strip().startswith("•")]
            detail = "\n".join(non_bullet_lines).strip() if non_bullet_lines else ""
        else:
            possible_causes = []

        context["insight"] = {
            "id": insight_record.id,
            "headline": insight_data.get("headline", ""),
            "detail": detail,
            "possible_causes": possible_causes,
            "recommendation": insight_data.get("recommendation", ""),
            "metric_cards": insight_data.get("metric_cards", []),
            "actions": resolved_actions,
            "is_fallback": insight_data.get("is_fallback", False),
            "generated_at": insight_record.updated_at,
        }
        # Include snapshot for feedback system
        context["insight_snapshot"] = json.dumps(insight_data)

    return TemplateResponse(
        request,
        "metrics/partials/engineering_insights.html",
        context,
    )


@login_and_team_required
def background_progress(request: HttpRequest) -> HttpResponse:
    """Return the background progress banner for HTMX polling.

    Used during Two-Phase Onboarding when Phase 2 is processing
    historical data in the background.
    """
    context = {
        "team": request.team,
        "show_complete_message": False,
    }

    # If background processing just completed, show success message briefly
    # Check if status transitioned from background to complete
    if request.team.onboarding_pipeline_status == "complete":
        # Check if we should show the completion message
        # (only once per session, using a simple session flag)
        session_key = f"bg_complete_shown_{request.team.id}"
        if not request.session.get(session_key):
            context["show_complete_message"] = True
            request.session[session_key] = True

    return TemplateResponse(
        request,
        "metrics/partials/background_progress_banner.html",
        context,
    )


@require_POST
@login_and_team_required
def refresh_insight(request: HttpRequest) -> HttpResponse:
    """Regenerate an insight on demand (HTMX endpoint).

    Query params:
        days: Number of days for the insight period (7, 30, or 90)
    """
    from datetime import timedelta

    from apps.metrics.services.insight_llm import (
        cache_insight,
        gather_insight_data,
        generate_insight,
    )

    days = int(request.GET.get("days") or 30)
    today = date.today()
    start_date = today - timedelta(days=days)

    context = {
        "days": days,
        "insight": None,
        "error": None,
    }

    try:
        # Generate fresh insight
        data = gather_insight_data(
            team=request.team,
            start_date=start_date,
            end_date=today,
        )
        insight = generate_insight(data)

        # Cache it with days as comparison_period
        cache_insight(
            team=request.team,
            insight=insight,
            target_date=today,
            days=days,
        )

        context["insight"] = {
            "headline": insight.get("headline", ""),
            "detail": insight.get("detail", ""),
            "recommendation": insight.get("recommendation", ""),
            "metric_cards": insight.get("metric_cards", []),
            "is_fallback": insight.get("is_fallback", False),
            "generated_at": timezone.now(),
        }
    except Exception as e:
        context["error"] = str(e)

    return TemplateResponse(
        request,
        "metrics/partials/engineering_insights.html",
        context,
    )
