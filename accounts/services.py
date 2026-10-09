"""Helpers for the emailed links used by email-verification and password-reset."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from notifications.services import send_plain_email

User = get_user_model()


def make_uid_and_token(user):
    """uid = user id in a URL-safe form; token = one-time signed code."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def get_user_from_uid_and_token(uid, token):
    """Return the user if uid+token are valid, else None."""
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None
    if default_token_generator.check_token(user, token):
        return user
    return None


def send_verification_email(user):
    uid, token = make_uid_and_token(user)
    link = f"{settings.SITE_URL}/api/auth/verify-email/?uid={uid}&token={token}"
    send_plain_email(
        user.email,
        "Verify your email address",
        f"Hi {user.username},\n\nPlease verify your email by opening this link:\n{link}\n",
    )


def send_password_reset_email(user):
    uid, token = make_uid_and_token(user)
    send_plain_email(
        user.email,
        "Reset your password",
        "Hi {name},\n\nTo reset your password, send a POST request to "
        "{site}/api/auth/reset-password/confirm/ with:\n"
        '  {{"uid": "{uid}", "token": "{token}", "new_password": "<your new password>"}}\n\n'
        "If you did not ask for this, ignore this email.\n".format(
            name=user.username, site=settings.SITE_URL, uid=uid, token=token
        ),
    )
