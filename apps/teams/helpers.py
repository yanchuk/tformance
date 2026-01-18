from allauth.account.models import EmailAddress
from django.contrib.auth.models import AnonymousUser
from django.db.models import F
from django.http import HttpRequest
from django.utils.translation import gettext as _

from apps.users.models import CustomUser
from apps.utils.slug import get_next_unique_slug

from . import roles
from .models import Invitation, Team


def get_default_team_name_for_user(user: CustomUser) -> str:
    return (user.get_display_name().split("@")[0] or _("My Team")).title()


def get_next_unique_team_slug(team_name: str) -> str:
    """
    Gets the next unique slug based on the name. Appends -1, -2, etc. until it finds
    a unique value.
    :param team_name:
    :return:
    """
    return get_next_unique_slug(Team, team_name[:40], "slug")


def get_team_for_request(request, view_kwargs) -> Team | None:
    """
    Get the team for a request.

    Team resolution order:
    1. ?team= query parameter (for direct team switching via URL)
    2. team ID in session (from previous requests)
    3. User's default (first) team

    Returns None if user is not authenticated or has no teams.
    """
    # For non-authenticated users, no team
    if not request.user.is_authenticated:
        return None

    # Check for ?team= query parameter (allows direct team switching via URL)
    team_id_param = request.GET.get("team")
    if team_id_param:
        try:
            team = request.user.teams.get(id=int(team_id_param))
            # Store in session so subsequent requests use this team
            request.session["team"] = team.id
            return team
        except (Team.DoesNotExist, ValueError):
            # Invalid team ID or user isn't a member - fall through to other methods
            pass

    # Check session for team ID
    if "team" in request.session:
        try:
            return request.user.teams.get(id=request.session["team"])
        except Team.DoesNotExist:
            # Team from session doesn't exist or user isn't a member
            del request.session["team"]

    # Fall back to user's first team
    return request.user.teams.first()


def get_default_team_from_request(request: HttpRequest) -> Team | None:
    if isinstance(request.user, AnonymousUser):
        return None
    if "team" in request.session:
        try:
            return request.user.teams.get(id=request.session["team"])
        except Team.DoesNotExist:
            # user wasn't member of team from session, or it didn't exist.
            # fall back to default behavior
            del request.session["team"]
            pass
    return get_default_team_for_user(request.user)


def get_default_team_for_user(user: CustomUser) -> Team | None:
    if user.teams.exists():
        return user.teams.first()
    return None


def create_default_team_for_user(user: CustomUser, team_name: str | None = None):
    team_name = team_name or get_default_team_name_for_user(user)
    slug = get_next_unique_team_slug(team_name)
    # unicode characters aren't allowed
    if not slug:
        slug = get_next_unique_team_slug(get_default_team_name_for_user(user))
    if not slug:
        slug = get_next_unique_team_slug("team")
    team = Team.objects.create(name=team_name, slug=slug)
    team.members.add(user, through_defaults={"role": roles.ROLE_ADMIN})
    team.save()
    return team


def get_open_invitations_for_user(user: CustomUser) -> list[dict]:
    user_emails = list(EmailAddress.objects.filter(user=user).order_by("-primary"))
    if not user_emails:
        return []

    emails = {e.email for e in user_emails}
    open_invitations = (
        Invitation.objects.filter(email__in=list(emails), is_accepted=False)
        .exclude(
            # don't show invitations for teams user is already a member of
            team__membership__user=user
        )
        .annotate(team_name=F("team__name"))
        .values("id", "team_name", "email")
    )
    verified_emails = {email.email for email in user_emails if email.verified}
    return [{**invitation, "verified": invitation["email"] in verified_emails} for invitation in open_invitations]
