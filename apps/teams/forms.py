from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.users.forms import TurnstileSignupForm

from .models import Invitation, Membership, Team


class TeamSignupForm(TurnstileSignupForm):
    """Signup form for new users.

    Users sign up without creating a team - teams are created during onboarding
    when the user connects their GitHub organization.

    Invitations are still supported - users with invitation_id will join the
    existing team after signup.
    """

    invitation_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    terms_agreement = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # blank out overly-verbose help text
        self.fields["password1"].help_text = ""
        # Use format_html instead of mark_safe for safer HTML construction
        terms_url = reverse("web:terms")
        privacy_url = reverse("web:privacy")
        self.fields["terms_agreement"].label = format_html(
            'I agree to the <a class="link" href="{}" target="_blank">Terms of Service</a> '
            'and <a class="link" href="{}" target="_blank">Privacy Policy</a>',
            terms_url,
            privacy_url,
        )

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            self._clean_invitation_email(cleaned_data)
        return cleaned_data

    def _clean_invitation_email(self, cleaned_data):
        invitation_id = cleaned_data.get("invitation_id")
        if invitation_id:
            try:
                invite = Invitation.objects.get(id=invitation_id)
            except (Invitation.DoesNotExist, ValidationError):
                # ValidationError is raised if the ID isn't a valid UUID, which should be treated the same
                # as not found
                raise forms.ValidationError(
                    _(
                        "That invitation could not be found. "
                        "Please double check your invitation link or sign in to continue."
                    )
                ) from None

            if invite.is_accepted:
                raise forms.ValidationError(
                    _(
                        "It looks like that invitation link has expired. "
                        "Please request a new invitation or sign in to continue."
                    )
                )

            email = cleaned_data.get("email")  # this is always lowercase via form validation
            if invite.email.lower() != email:
                raise forms.ValidationError(
                    _("You must sign up with the email address that the invitation was sent to.")
                )

    def save(self, request):
        # No team creation here - teams are created during onboarding
        # when user connects GitHub organization.
        # Invitation handling is done in signals.py
        return super().save(request)


class TeamChangeForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ("name",)
        labels = {
            "name": _("Team Name"),
        }
        help_texts = {
            "name": _("Your team name."),
        }


class InvitationForm(forms.ModelForm):
    def __init__(self, team, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        # confirm no other pending invitations for this email
        if Invitation.objects.filter(team=self.team, email__iexact=email, is_accepted=False):
            raise ValidationError(
                _(
                    'There is already a pending invitation for {}. You can resend it by clicking "Resend Invitation".'
                ).format(email)
            )
        # and the user isn't a member
        if Membership.objects.filter(team=self.team, user__email__iexact=email).exists():
            raise ValidationError(_("{email} is already a member of this team.").format(email=email))
        return email

    class Meta:
        model = Invitation
        fields = ("email", "role")


class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ("role",)
