"""
Run with:  python manage.py seed_demo
Creates demo data so you can try the API immediately:
  admin  : admin@example.com  / Admin#12345
  agent  : agent@example.com  / Agent#12345  (already approved)
  user   : user@example.com   / User#12345
plus the 7 categories from the requirements and a few properties.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from agents.models import AgentProfile
from properties.models import Category, Property

User = get_user_model()

CATEGORIES = ["Apartment", "Duplex", "Land", "Office Space", "Commercial Property", "Short-let", "Warehouse"]


class Command(BaseCommand):
    help = "Create demo users, categories and properties."

    def handle(self, *args, **options):
        if not User.objects.filter(email="admin@example.com").exists():
            username = "demo_admin" if User.objects.filter(username="demo_admin").exists() else "admin"
            User.objects.create_superuser("admin", "admin@example.com", "Admin#12345",
                                          is_email_verified=True)
        agent, created = User.objects.get_or_create(
            email="agent@example.com",
            defaults={"username": "demo_agent", "role": "agent", "is_email_verified": True})
        if created:
            agent.set_password("Agent#12345")
            agent.save()
        AgentProfile.objects.get_or_create(user=agent, defaults={
            "company_name": "Lagos Prime Realty", "license_number": "LPR-001", "status": "approved"})
        user, created = User.objects.get_or_create(
            email="user@example.com", defaults={"username": "demo_user", "is_email_verified": True})
        if created:
            user.set_password("User#12345")
            user.save()

        cats = {name: Category.objects.get_or_create(name=name)[0] for name in CATEGORIES}
        samples = [
            ("3-Bedroom Duplex in Lekki", "duplex", "Duplex", 85000000, "for_sale", 3, 4, "Lekki", ["pool", "generator"]),
            ("Cozy 2-Bedroom Apartment", "apt", "Apartment", 1500000, "for_rent", 2, 2, "Yaba", ["parking"]),
            ("Plot of Land, Ibeju-Lekki", "land", "Land", 12000000, "for_sale", 0, 0, "Ibeju-Lekki", []),
        ]
        for title, _, cat, price, status, beds, baths, city, amen in samples:
            Property.objects.get_or_create(title=title, defaults=dict(
                description=f"{title}. Great location.", price=price, property_type=cats[cat],
                status=status, bedrooms=beds, bathrooms=baths, square_feet=1200,
                address=f"12 Example Street, {city}", city=city, state="Lagos", country="Nigeria",
                amenities=amen, publication_status="published", created_by=agent))
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
