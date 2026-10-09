"""
Run with:  python manage.py send_inspection_reminders
Emails everyone who has an APPROVED inspection in the next 24 hours.
Put it in a cron job (or Celery beat later) to run every hour.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from inspections.models import InspectionBooking
from notifications.models import Notification
from notifications.services import notify


class Command(BaseCommand):
    help = "Send reminders for inspections happening in the next 24 hours."

    def handle(self, *args, **options):
        now = timezone.now()
        upcoming = InspectionBooking.objects.filter(
            status=InspectionBooking.Status.APPROVED, reminder_sent=False,
            scheduled_at__gt=now, scheduled_at__lte=now + timedelta(hours=24),
        ).select_related("property", "user")
        count = 0
        for booking in upcoming:
            text = (f'Reminder: inspection of "{booking.property.title}" '
                    f"at {booking.scheduled_at:%d %b %Y %H:%M}.")
            notify(booking.user, "Inspection reminder", text, Notification.Type.INSPECTION)
            notify(booking.property.created_by, "Inspection reminder", text, Notification.Type.INSPECTION)
            booking.reminder_sent = True
            booking.save(update_fields=["reminder_sent"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Sent {count} reminder(s)."))
