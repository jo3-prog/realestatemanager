"""
A tiny "service" used by every other app to notify people.

Keeping this in ONE place (instead of copy-pasting send_mail everywhere)
is what the requirements call "reusable services".
"""
from django.conf import settings
from django.core.mail import send_mail

from .models import Notification


def notify(user, title, message, notification_type=Notification.Type.GENERAL):
    """Save an in-app notification AND send an email to the user."""
    notification = Notification.objects.create(
        user=user, title=title, message=message, notification_type=notification_type
    )
    if user.email:
        # fail_silently=True: a broken mail server must not break the API call.
        send_mail(
            subject=title,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    return notification


def send_plain_email(to_email, subject, message):
    """Email someone who might not have an account (e.g. an anonymous inquirer)."""
    send_mail(
        subject, message, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=True
    )
