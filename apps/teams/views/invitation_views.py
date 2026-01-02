import uuid

from allauth.account.models import EmailAddress
from allauth.account.views import SignupView
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from apps.users.models import CustomUser
from apps.utils.analytics import track_event, update_team_properties, update_user_properties

from ..invitations import clear_invite_from_session, process_invitation
from ..models import Invitation
from ..roles import is_member


def accept_invitation(request, invitation_id):
    # Validate UUID format before database lookup
    try:
        uuid.UUID(str(invitation_id))
    except (ValueError, TypeError):
        raise Http404("Invalid invitation ID") from None

    invitation = get_object_or_404(Invitation, id=invitation_id)
    if not invitation.is_accepted:
        # set invitation in the session in case needed later - e.g. to redirect after login
        request.session["invitation_id"] = invitation_id
    else:
        clear_invite_from_session(request)
    if request.user.is_authenticated and is_member(request.user, invitation.team):
        messages.info(
            request,
            _("It looks like you're already a member of {team}. You've been redirected.").format(
                team=invitation.team.name
            ),
        )
        return HttpResponseRedirect(reverse("web:home"))

    if request.method == "POST":
        # accept invitation workflow
        if not request.user.is_authenticated:
            messages.error(request, _("Please log in again to accept your invitation."))
            return HttpResponseRedirect(reverse("account_login"))
        else:
            if invitation.is_accepted:
                messages.error(request, _("Sorry, it looks like that invitation link has expired."))
                return HttpResponseRedirect(reverse("web:home"))
            else:
                # Calculate invite age before accepting (invitation.created_at is available)
                invite_age_days = (timezone.now() - invitation.created_at).days

                process_invitation(invitation, request.user)
                clear_invite_from_session(request)

                # Track team member joined event
                track_event(
                    request.user,
                    "team_member_joined",
                    {
                        "team_slug": invitation.team.slug,
                        "invite_age_days": invite_age_days,
                        "joined_via": "invite",
                    },
                )

                # Update user and team properties after join
                update_user_properties(
                    request.user,
                    {"teams_count": request.user.teams.count()},
                )
                update_team_properties(
                    invitation.team,
                    {"member_count": invitation.team.members.count()},
                )

                messages.success(request, _("You successfully joined {}").format(invitation.team.name))
                return HttpResponseRedirect(reverse("web:home"))

    account_exists = CustomUser.objects.filter(email=invitation.email).exists()
    owned_email_address = None
    user_team_count = 0
    if request.user.is_authenticated:
        owned_email_address = EmailAddress.objects.filter(email=invitation.email, user=request.user).first()
        user_team_count = request.user.teams.count()
    return render(
        request,
        "teams/accept_invite.html",
        {
            "invitation": invitation,
            "account_exists": account_exists,
            "user_owns_email": bool(owned_email_address),
            "email_verified": owned_email_address and owned_email_address.verified,
            "user_team_count": user_team_count,
        },
    )


class SignupAfterInvite(SignupView):
    @cached_property
    def invitation(self) -> Invitation:
        from ..models import Invitation

        invitation_id = self.kwargs["invitation_id"]

        # Validate UUID format before database lookup
        try:
            uuid.UUID(str(invitation_id))
        except (ValueError, TypeError):
            raise Http404("Invalid invitation ID") from None

        invitation = get_object_or_404(Invitation, id=invitation_id)
        if invitation.is_accepted:
            messages.error(self.request, _("Sorry, it looks like that invitation link has expired."))
            raise Http404
        return invitation

    def get_initial(self):
        initial = super().get_initial()
        if self.invitation:
            initial["team_name"] = self.invitation.team.name
            initial["email"] = self.invitation.email
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.invitation:
            context["invitation"] = self.invitation
        return context

    def form_valid(self, form):
        response = super().form_valid(form)

        # Mark the email as verified since it was used in the invitation
        if settings.ACCOUNT_EMAIL_VERIFICATION != "none" and hasattr(self, "user") and self.invitation:
            from allauth.account.models import EmailAddress

            email_address = EmailAddress.objects.filter(user=self.user, email=self.invitation.email).first()
            if email_address:
                email_address.set_verified(commit=True)

        return response
