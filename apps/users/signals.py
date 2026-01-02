import logging

from allauth.account.signals import email_confirmed, user_signed_up
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.files.storage import default_storage
from django.core.mail import mail_admins
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from apps.users.models import CustomUser
from apps.utils.analytics import identify_user, track_event

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def rotate_session_on_login(sender, request, user, **kwargs):
    """Rotate session key on login to prevent session fixation attacks.

    This creates a new session ID while preserving session data,
    ensuring any pre-authentication session ID cannot be reused.
    """
    if hasattr(request, "session"):
        request.session.cycle_key()
        logger.debug(f"Session rotated for user {user.email}")


@receiver(user_signed_up)
def handle_sign_up(request, user, **kwargs):
    # customize this function to do custom logic on sign up, e.g. send a welcome email
    # or subscribe them to your mailing list.
    # This example notifies the admins, in case you want to keep track of sign ups
    _notify_admins_of_signup(user)

    # Track signup in PostHog
    # Determine signup method from sociallogin if available
    sociallogin = kwargs.get("sociallogin")
    signup_source = sociallogin.account.provider if sociallogin else "email"

    # Identify user with initial properties including signup source
    identify_user(
        user,
        {
            "signup_source": signup_source,
            "teams_count": 0,
            "has_connected_github": False,
            "has_connected_jira": False,
            "has_connected_slack": False,
        },
    )
    track_event(user, "user_signed_up", {"method": signup_source})


@receiver(email_confirmed)
def update_user_email(sender, request, email_address, **kwargs):
    """
    When an email address is confirmed make it the primary email.
    """
    # This also sets user.email to the new email address.
    # hat tip: https://stackoverflow.com/a/29661871/8207
    email_address.set_as_primary()


def _notify_admins_of_signup(user):
    mail_admins(
        f"Yowsers, someone signed up for {settings.PROJECT_METADATA['NAME']}!",
        f"Email: {user.email}",
        fail_silently=True,
    )


@receiver(pre_save, sender=CustomUser)
def remove_old_profile_picture_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return False

    try:
        old_file = sender.objects.get(pk=instance.pk).avatar
    except sender.DoesNotExist:
        return False

    if old_file and old_file.name != instance.avatar.name and default_storage.exists(old_file.name):
        default_storage.delete(old_file.name)


@receiver(post_delete, sender=CustomUser)
def remove_profile_picture_on_delete(sender, instance, **kwargs):
    if instance.avatar and default_storage.exists(instance.avatar.name):
        default_storage.delete(instance.avatar.name)
