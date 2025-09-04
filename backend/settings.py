"""
Django settings for dsp_backend project - Production Ready
"""

import os
import dj_database_url
from pathlib import Path
from datetime import timedelta

# .env Datei laden für Development
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-2u17c0synl42*!h34-1b^f+hzfo(1exfv_el7$lm(bec9*hq+b"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

# Production-ready ALLOWED_HOSTS
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition
INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    # Third Party Apps
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    # Local Apps
    "elearning.apps.ElearningConfig",
    "core.microsoft_services.apps.MicrosoftServicesConfig",
    "db_overview.apps.DbOverviewConfig",
    "core.employees.apps.EmployeesConfig",
    "shift_planner.apps.ShiftPlannerConfig",
    # Stripe App
    "djstripe",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# CORS Settings - Production-ready
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174"
).split(",")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "cache-control",
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:517[0-9]$",
    r"^http://127\.0\.0\.1:517[0-9]$",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

# Database - Production-ready mit PostgreSQL
if os.environ.get("DATABASE_URL"):
    # Production: PostgreSQL auf Render.com
    DATABASES = {"default": dj_database_url.parse(os.environ.get("DATABASE_URL"))}
else:
    # Development: SQLite
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Cache Configuration - Production-ready mit Redis
if os.environ.get("REDIS_URL"):
    # Production: Redis auf Render.com
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.environ.get("REDIS_URL"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 20,
                    "retry_on_timeout": True,
                },
                "PARSER_CLASS": "redis.connection.HiredisParser",
                "PICKLE_VERSION": -1,
            },
        }
    }
    # Session Backend für Production (optional - OAuth nutzt jetzt Cache direkt)
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    # Development: In-Memory Cache
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "oauth-state-cache",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images) - Production-ready
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Security Settings für Production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework Settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
}

# Simple JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "15"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.environ.get("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "1"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# Email Settings
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@datasmartpoint.com")

# Frontend URL für Links in Emails etc.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", "3600"))

# Microsoft Azure AD Settings für Organization Authentication
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")

# Optional: Erlaubte Email-Domains für zusätzliche Sicherheit
DSP_ALLOWED_DOMAINS = [
    # Füge hier eure Organisation-Domains hinzu
    "datasmartpoint.com"
]

# Jazzmin Settings (bleiben unverändert)
JAZZMIN_SETTINGS = {
    # Titel der Seite (Angepasst für das neue Projekt)
    "site_title": "DSP Admin",
    "site_header": "DSP Backend",
    "site_brand": "DSP Backend",
    "site_logo": None,
    "login_logo": None,
    "login_logo_dark": None,
    "site_logo_classes": "img-circle",
    "site_icon": None,
    "welcome_sign": "Willkommen im DSP Admin-Bereich",
    "copyright": "DSP Team",
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Website", "url": "/", "new_window": True},
    ],
    "usermenu_links": [
        {"name": "Mein Profil", "url": "admin:auth_user_change", "id_field": "user.id"},
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "elearning": "fas fa-graduation-cap",
    },
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user": "collapsible",
    },
    "order_with_respect_to": [
        "auth",
        "elearning",
    ],
    "user_avatar": None,
    "custom_css": None,
    "custom_js": None,
}

# Jazzmin UI-Anpassungen
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}

# ---- Payments / Stripe / dj-stripe ----
# Stripe integration using dj-stripe.
# We support both TEST mode (development/sandbox) and LIVE mode (production).
# Which environment is active depends on STRIPE_LIVE_MODE.

# Mode toggle
#    - If STRIPE_LIVE_MODE=True → project uses LIVE Stripe environment (real payments).
#    - If STRIPE_LIVE_MODE=False → project uses TEST environment (fake payments).
STRIPE_LIVE_MODE = os.environ.get("STRIPE_LIVE_MODE", "False").lower() == "true"


# Secret keys (backend only)
#    - Used by Django (server) to communicate with Stripe API.
#    - These keys allow creating customers, payment intents, subscriptions, etc.
#    - NEVER expose to frontend or commit to GitHub.
STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "")  # sk_test_xxx
STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "")  # sk_live_xxx


# Publishable keys (frontend safe)
#    - Used by the React frontend to initialize Stripe.js and create payment tokens.
#    - These keys are safe to expose in the browser.
#    - They cannot directly charge customers — only generate secure tokens.
STRIPE_TEST_PUBLISHABLE_KEY = os.environ.get(
    "STRIPE_TEST_PUBLISHABLE_KEY", ""
)  # pk_test_xxx
STRIPE_LIVE_PUBLISHABLE_KEY = os.environ.get(
    "STRIPE_LIVE_PUBLISHABLE_KEY", ""
)  # pk_live_xxx


# Webhook secret
#    - Each webhook endpoint you configure in Stripe Dashboard has a unique signing secret.
#    - This is required to verify that incoming webhook requests (e.g., "payment succeeded")
#      really come from Stripe and were not faked.
DJSTRIPE_WEBHOOK_SECRET = os.environ.get("DJSTRIPE_WEBHOOK_SECRET", "")


# Default currency
#    - The currency that will be used for payments if no other is specified.
#    - Example: "eur" for Euro, "usd" for US Dollar.
#    - Can be overridden per transaction if needed.
DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "eur")


# Stripe API version
#    - Ensures dj-stripe and your project use a consistent Stripe API version.
#    - Set to the version displayed in your Stripe Dashboard under:
#      Developers → API Version.
DJSTRIPE_STRIPE_API_VERSION = os.environ.get(
    "DJSTRIPE_STRIPE_API_VERSION", "2024-06-20"
)


# Active secret key at runtime
#    - dj-stripe looks at STRIPE_SECRET_KEY for making all API calls.
#    - We dynamically set it based on STRIPE_LIVE_MODE.
STRIPE_SECRET_KEY = (
    STRIPE_LIVE_SECRET_KEY if STRIPE_LIVE_MODE else STRIPE_TEST_SECRET_KEY
)

# dj-stripe relation mode:
# - "id"         → (new installs) use Stripe object "id" (e.g., "cus_...") as FK target
# - "djstripe_id"→ (legacy installs) use dj-stripe’s internal PK
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"
