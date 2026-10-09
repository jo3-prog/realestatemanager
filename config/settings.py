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
RENDER_HOST = env("RENDER_EXTERNAL_HOSTNAME", None)  # used in production on Render.com
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)  # add the Render hostname to allowed hosts
TESTING = "test" in sys.argv  # True when running `python manage.py test`

USE_CLOUDINARY = bool(env("CLOUDINARY_URL"))

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
if USE_CLOUDINARY:
    # used only when cloudinary url is set: images go to cloudinary
    INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]

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

# Database... 
# SQLite needs no setup (perfect for development). To use PostgreSQL set
# DB_ENGINE=postgres and the DB_* variables in your .env file.
if env ("DATABASE_URL"): 
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.config(conn_max_age=600, conn_health_checks=True)
    }
elif env("DB_ENGINE") == "postgres":
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

# Use user model (accounts.User) instead of Django's default one.
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

# Django uses storages to choose where files live
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}
if USE_CLOUDINARY:
    # if cloudinary url is set, use cloudinary for uploaded files
    STORAGES["default"] = {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
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

# CORS
CORS_ALLOWED_ORIGINS = DEBUG 
CORS_ALLOWED_ORIGINS = [
    o.strip().rstrip("/") for o in env("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]

# Email
# Default: emails are PRINTED in your terminal (great for learning).
# For real emails set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# and the EMAIL_* variables ---- this is handled by resend.
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
if env("RESEND_API_KEY"):
    # Use resend.com to send real emails (see README for setup instructions).
    EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
    INSTALLED_APPS += ["anymail"]
    ANYMAIL = {"RESEND_API_KEY": env("RESEND_API_KEY")}
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@realestate.local")

# Base URL used inside emailed links (a frontend would normally own these).
SITE_URL = env("SITE_URL") or env("RENDER_EXTERNAL_URL") or "http://127.0.0.1:8000"

# If True, users cannot log in until they verify their email address.
REQUIRE_EMAIL_VERIFICATION = env("REQUIRE_EMAIL_VERIFICATION", "False") == "True"

# Faster password hashing ONLY while running tests (never do this in production!)
if TESTING:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
