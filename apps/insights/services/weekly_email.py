"""Weekly insight email service.

Sends automated weekly insight emails to team administrators with
AI-generated summaries of team performance and metrics.
"""

import logging
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import send_mail

from apps.metrics.models import DailyInsight
from apps.teams import roles
from apps.teams.models import Membership, Team

logger = logging.getLogger(__name__)


def get_latest_weekly_insight(team: Team) -> DailyInsight | None:
    """Get the latest weekly insight for the current week.

    Args:
        team: The team to get insights for

    Returns:
        DailyInsight or None if no insight exists for the current week
    """
    monday = date.today() - timedelta(days=date.today().weekday())
    return DailyInsight.objects.filter(  # noqa: TEAM001 - filtered by team parameter
        team=team,
        category="llm_insight",
        comparison_period="7",
        date=monday,
    ).first()


def send_weekly_insight_email(team: Team) -> dict:
    """Send weekly insight email to team admins.

    Args:
        team: The team to send emails for

    Returns:
        dict with sent_to count and skipped_reason (if any)
    """
    insight = get_latest_weekly_insight(team)
    if not insight:
        logger.info("Skipping weekly email for team %s: no insight available", team.slug)
        return {"sent_to": 0, "skipped_reason": "no_insight"}

    admin_memberships = Membership.objects.filter(
        team=team,
        role=roles.ROLE_ADMIN,
    ).select_related("user")

    admins_with_email = [m.user for m in admin_memberships if m.user.email]
    if not admins_with_email:
        logger.info("Skipping weekly email for team %s: no admins with email", team.slug)
        return {"sent_to": 0, "skipped_reason": "no_admin_emails"}

    headline = insight.metric_value.get("headline", "Your Team Summary")
    detail = insight.metric_value.get("detail", "")
    subject = f"Weekly Insight: {headline}"

    base_url = getattr(settings, "PROJECT_METADATA", {}).get("URL", "http://localhost:8000")
    dashboard_url = f"{base_url}/app/"

    sent_count = 0
    for admin in admins_with_email:
        first_name = admin.first_name or "there"
        body = f"""Hi {first_name},

Here's the weekly insight for {team.name}:

{headline}

{detail}

View your dashboard: {dashboard_url}
"""
        send_mail(
            subject=subject,
            message=body,
            from_email=None,
            recipient_list=[admin.email],
            fail_silently=True,
        )
        sent_count += 1

    logger.info("Sent weekly insight email to %d admins for team %s", sent_count, team.slug)
    return {"sent_to": sent_count, "skipped_reason": None}
