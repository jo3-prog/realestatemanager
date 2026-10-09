"""Small factory helpers shared by all test files."""
import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from agents.models import AgentProfile
from properties.models import Category, Property

User = get_user_model()
PASSWORD = "StrongPass#123"


def make_user(email="user@example.com", role=User.Role.USER, **extra):
    return User.objects.create_user(
        username=email.split("@")[0], email=email, password=PASSWORD, role=role, **extra)


def make_admin(email="admin@example.com"):
    return User.objects.create_superuser(username="admin", email=email, password=PASSWORD)


def make_agent(email="agent@example.com", approved=True):
    user = make_user(email, role=User.Role.AGENT)
    AgentProfile.objects.create(
        user=user, company_name="Acme Realty", license_number="LIC-1",
        status=AgentProfile.Status.APPROVED if approved else AgentProfile.Status.PENDING)
    return user


def client_for(user=None):
    """An API client that is already logged in as `user` (or anonymous)."""
    client = APIClient()
    if user:
        client.force_authenticate(user=user)
    return client


def make_category(name="Apartment"):
    return Category.objects.create(name=name)


def make_property(agent, category=None, **overrides):
    data = dict(
        title="Nice flat", description="Lovely", price=1000000,
        property_type=category or make_category("Apartment-%s" % Category.objects.count()),
        status=Property.Status.FOR_SALE, bedrooms=3, bathrooms=2, square_feet=900,
        address="1 Main St", city="Lagos", state="Lagos", country="Nigeria",
        publication_status=Property.Publication.PUBLISHED, created_by=agent)
    data.update(overrides)
    return Property.objects.create(**data)


def property_payload(category_id, **overrides):
    data = {"title": "Cozy Duplex", "description": "Great place", "price": "2500000.00",
            "property_type": category_id, "status": "for_sale", "bedrooms": 4, "bathrooms": 3,
            "square_feet": 1500, "address": "5 Palm Rd", "city": "Lagos", "state": "Lagos",
            "country": "Nigeria", "amenities": ["pool", "gym"], "publication_status": "published"}
    data.update(overrides)
    return data


def png_file(name="pic.png"):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")
