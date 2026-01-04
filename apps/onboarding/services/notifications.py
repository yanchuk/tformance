"""Notification services for onboarding."""

from django.conf import settings
from django.core.mail import send_mail

from apps.teams.models import Team
from apps.users.models import CustomUser


def send_welcome_email(team: Team, user: CustomUser) -> bool:
    """Send welcome email after team creation during onboarding.

    Args:
        team: The newly created Team
        user: The user who completed onboarding

    Returns:
        True if email was sent, False if skipped (no email address)
    """
    if not user.email:
        return False

    # Determine greeting name
    name = user.first_name or "there"

    # Build dashboard URL using PROJECT_METADATA
    base_url = getattr(settings, "PROJECT_METADATA", {}).get("URL", "http://localhost:8000")
    dashboard_url = f"{base_url}/app/"

    subject = "Welcome to Tformance!"

    message = f"""Hi {name},

Welcome to Tformance! Your team "{team.name}" has been set up and is ready to go.

Your engineering metrics dashboard is now available at:
{dashboard_url}

What's next?
- View your PR metrics and cycle time analysis
- See AI tool adoption across your team
- Track your team's velocity and throughput

We're pulling in your historical data now. You'll receive another email when the initial sync is complete.

If you have any questions, reply to this email or visit our help center.

Thanks for choosing Tformance!
The Tformance Team
"""

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )

    return True


def send_sync_complete_email(team: Team, user: CustomUser, prs_synced: int, repos_synced: int) -> bool:
    """Send email notification when initial data sync is complete.

    Args:
        team: The Team whose data was synced
        user: The user to notify
        prs_synced: Number of pull requests synced
        repos_synced: Number of repositories synced

    Returns:
        True if email was sent, False if skipped (no email address)
    """
    if not user.email:
        return False

    # Determine greeting name
    name = user.first_name or "there"

    # Build dashboard URL using PROJECT_METADATA
    base_url = getattr(settings, "PROJECT_METADATA", {}).get("URL", "http://localhost:8000")
    dashboard_url = f"{base_url}/app/"

    subject = "Your Tformance data sync is complete!"

    message = f"""Hi {name},

Great news! We've finished syncing your GitHub data for {team.name}.

Here's what we imported:
- {repos_synced} repositories
- {prs_synced} pull requests

Your dashboard is now ready with historical metrics and insights. Check it out:
{dashboard_url}

What you can explore now:
- PR cycle time trends and review metrics
- AI tool adoption patterns across your team
- Team velocity and throughput analysis

If you haven't already, consider connecting Jira and Slack to get even more insights.

Thanks for using Tformance!
The Tformance Team
"""

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )

    return True
