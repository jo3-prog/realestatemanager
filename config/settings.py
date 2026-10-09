"""
Project settings.

settings.py is the "control panel" of a Django project. Every important
decision (which apps are installed, which database to use, how login works)
lives here. Secrets and things that change between your laptop and a real
server are read from environment variables (see .env.example).
"""
import os
import sys
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    """Small helper: read an environment variable, or use a default."""
    return os.environ.get(name, default)


SECRET_KEY = env("SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env("DEBUG", "True") == "True"
ALLOWED_HOSTS = env("ALLOWED_HOSTS", "127.0.0.1,localhost,testserver").split(",")
TESTING = "test" in sys.argv  # True when running `python manage.py test`

INSTALLED_APPS = [
    # Built into Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party packages
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",  # lets us "log out" a JWT
    "django_filters",
    "drf_spectacular",  # Swagger / ReDoc docs
    "corsheaders",
    # Our own apps
    "accounts",
    "agents",
    "properties",
    "inquiries",
    "inspections",
    "reviews",
    "notifications",
    "analytics",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must be near the top
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------- Database
# SQLite needs no setup (perfect for development). To use PostgreSQL set
# DB_ENGINE=postgres and the DB_* variables in your .env file.
if env("DB_ENGINE") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "realestate"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Use OUR User model (accounts.User) instead of Django's default one.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Uploaded files (property photos) are saved on disk in /media
# (you can swap this for Cloudinary later, see README).
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------ Django REST Framework
REST_FRAMEWORK = {
    # Every request is checked for a JWT token in the Authorization header.
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # Default = must be logged in. Views that are public say so explicitly.
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Rate limiting (security requirement)
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/day" if TESTING else "100/hour",
        "user": "100000/day" if TESTING else "1000/hour",
        "auth": "10000/day" if TESTING else "20/hour",  # login/register/reset
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Real Estate Sales & Leasing Management API",
    "DESCRIPTION": "Backend API for agents, listings, inquiries, inspections and more.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,  # needed for file upload docs
    # Several models have a field called "status"; give each choice list its own name.
    "ENUM_NAME_OVERRIDES": {
        "PropertyStatusEnum": "properties.models.Property.Status",
        "PublicationStatusEnum": "properties.models.Property.Publication",
        "AgentStatusEnum": "agents.models.AgentProfile.Status",
        "InquiryStatusEnum": "inquiries.models.Inquiry.Status",
        "InspectionStatusEnum": "inspections.models.InspectionBooking.Status",
    },
}

# ------------------------------------------------------------------- CORS
CORS_ALLOW_ALL_ORIGINS = DEBUG  # in production list real origins instead

# ------------------------------------------------------------------ Email
# Default: emails are PRINTED in your terminal (great for learning).
# For real emails set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# and the EMAIL_* variables.
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@realestate.local")

# Base URL used inside emailed links (a frontend would normally own these).
SITE_URL = env("SITE_URL", "http://127.0.0.1:8000")

# If True, users cannot log in until they verify their email address.
REQUIRE_EMAIL_VERIFICATION = env("REQUIRE_EMAIL_VERIFICATION", "False") == "True"

# Faster password hashing ONLY while running tests (never do this in production!)
if TESTING:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
