"""
Creates the frirst admin user if none exists. 
"""

import os 
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Creates the first admin user from env if none with that email exists."

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not email or not password:
            self.stdout.write("DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD must be set; skipping admin creation.")
            return 

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(f"Admin user with email {email} already exists; skipping creation.")

        # pick a username that doesn't exist yet (username must be unique)
        base = os.environ.get("DJANGO_SUPERUSER_USERNAME") or email.split("@")[0]
        username, n = base, 2
        while User.objects.filter(username=username).exists():
            username = f"{base}{n}"
            n += 1
        User.objects.create_superuser(username=username, email=email, password=password, is_email_verified=True)
        self.stdout.write(self.style.SUCCESS(f"Created admin {email}."))