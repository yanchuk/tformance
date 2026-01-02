from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.teams.decorators import login_and_team_required, team_admin_required
from apps.teams.forms import InvitationForm, TeamChangeForm
from apps.teams.helpers import get_next_unique_team_slug, get_open_invitations_for_user
from apps.teams.invitations import send_invitation
from apps.teams.models import Invitation
from apps.teams.roles import is_admin
from apps.utils.analytics import track_event
from apps.web.forms import set_form_fields_disabled


@login_required
def manage_teams(request):
    teams = request.user.teams.order_by("name")
    return render(
        request,
        "teams/list_teams.html",
        {
            "teams": teams,
            "invitations": get_open_invitations_for_user(request.user),
            "page_title": _("Manage Teams"),
        },
    )


@login_and_team_required
def manage_team(request):
    team = request.team
    team_form = None
    if request.method == "POST":
        if is_admin(request.user, team):
            team_form = TeamChangeForm(request.POST, instance=team)
            if team_form.is_valid():
                messages.success(request, _("Team details saved!"))
                team_form.save()
        else:
            messages.error(request, "Sorry you don't have permission to do that.")
    if team_form is None:
        team_form = TeamChangeForm(instance=team)
    if request.team_membership.role != "admin":
        set_form_fields_disabled(team_form, True)

    return render(
        request,
        "teams/manage_team.html",
        {
            "team": team,
            "active_tab": "manage-team",
            "page_title": _("My Team | {team}").format(team=team),
            "team_form": team_form,
            "invitation_form": InvitationForm(team=request.team),
            "pending_invitations": Invitation.objects.filter(team=team, is_accepted=False).order_by("-created_at"),
        },
    )


@login_required
def create_team(request):
    if request.method == "POST":
        form = TeamChangeForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.slug = get_next_unique_team_slug(team.name)
            team.save()
            team.members.add(request.user, through_defaults={"role": "admin"})
            return HttpResponseRedirect(reverse("teams:manage_teams"))
    else:
        form = TeamChangeForm()
    return render(
        request,
        "teams/manage_team.html",
        {
            "team_form": form,
            "create": True,
            "page_title": _("Create Team"),
        },
    )


@team_admin_required
@require_POST
def delete_team(request):
    request.team.delete()
    messages.success(request, _('The "{team}" team was successfully deleted').format(team=request.team.name))
    return HttpResponseRedirect(reverse("web:home"))


@team_admin_required
@require_POST
def resend_invitation(request, invitation_id):
    invitation = get_object_or_404(Invitation, team=request.team, id=invitation_id)
    send_invitation(invitation)
    return HttpResponse('<span class="pg-button-light is-disbled btn-disabled">Sent!</span>')


@team_admin_required
@require_POST
def send_invitation_view(request):
    form = InvitationForm(request.team, request.POST)
    if form.is_valid():
        invitation = form.save(commit=False)
        invitation.team = request.team
        invitation.invited_by = request.user
        try:
            # we have to do validation again on the model because the team wasn't set when form validation happened
            invitation.validate_unique()
        except ValidationError as e:
            form.add_error(None, e.messages[0])
        else:
            invitation.save()
            send_invitation(invitation)

            # Track team member invited event
            track_event(
                request.user,
                "team_member_invited",
                {
                    "team_slug": request.team.slug,
                    "inviter_role": request.team_membership.role,
                    "invite_method": "email",
                },
            )

            form = InvitationForm(request.team)  # clear saved data from the form
    else:
        pass
    return render(
        request,
        "teams/components/team_invitations.html",
        {
            "invitation_form": form,
            "pending_invitations": Invitation.objects.filter(team=request.team, is_accepted=False).order_by(
                "-created_at"
            ),
        },
    )


@team_admin_required
@require_POST
def cancel_invitation_view(request, invitation_id):
    invitation = get_object_or_404(Invitation, team=request.team, id=invitation_id)
    invitation.delete()
    return HttpResponse("")
