from pathlib import Path
import os
import sys
from decouple import config, Csv
from datetime import timedelta
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Check if running tests
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

_INSECURE_SECRET_DEFAULT = 'django-insecure-dev-key-change-in-production'

SECRET_KEY = config('SECRET_KEY', default=_INSECURE_SECRET_DEFAULT)
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

ORGANISATION_CREATION_ENABLED = config(
    "ORGANISATION_CREATION_ENABLED", default=True, cast=bool
)

INSTALLED_APPS = [
    'admin_panel',
    'accounts',
    'exams',
    'monitoring',
    'attempt_events',
    'organisations',
    'rest_framework',
    'corsheaders',
    'django_ratelimit',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django_ratelimit.middleware.RatelimitMiddleware',
    'core.middleware.MinimumAppVersionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='parallaxlane'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=600, cast=int),  # 10 minutes
    }
}

if not DEBUG and not TESTING:
    _required_database_environment = {
        "DB_NAME": config("DB_NAME", default=None),
        "DB_USER": config("DB_USER", default=None),
        "DB_PASSWORD": config("DB_PASSWORD", default=None),
        "DB_HOST": config("DB_HOST", default=None),
    }
    _missing_database_environment = [
        name for name, value in _required_database_environment.items() if not value
    ]
    if _missing_database_environment:
        raise ImproperlyConfigured(
            "Missing required production database settings: "
            + ", ".join(_missing_database_environment)
        )

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=DEBUG, cast=bool)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())

AUTH_USER_MODEL = "accounts.User"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

import logging

_settings_logger = logging.getLogger(__name__)

REDIS_URL = config("REDIS_URL", default=None)
# When False, always use LocMemCache (recommended for local dev without Docker Redis).
USE_REDIS_CACHE = config("USE_REDIS_CACHE", default=False, cast=bool)
# When True and Redis is unreachable at startup, raise instead of falling back.
REDIS_REQUIRED = config("REDIS_REQUIRED", default=not DEBUG, cast=bool)
# For django_ratelimit
RATELIMIT_VIEW = "core.views.ratelimit_error"  # Dummy view name (doesn't need to exist)
RATELIMIT_ENABLE = config("RATELIMIT_ENABLE", default=True, cast=bool)
# Availability during an exam beats a short window of unthrottled requests:
# when the cache is unreachable, let requests through instead of blocking all.
RATELIMIT_FAIL_OPEN = config("RATELIMIT_FAIL_OPEN", default=True, cast=bool)
# Client IP for per-IP limits (see core/ratelimit.py).
RATELIMIT_IP_META_KEY = "core.ratelimit.client_ip"
TRUST_PROXY_IP_HEADER = config("TRUST_PROXY_IP_HEADER", default=False, cast=bool)

_LOC_MEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


def _redis_is_reachable(url: str) -> bool:
    try:
        import redis

        client = redis.from_url(
            url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        return True
    except Exception as exc:
        _settings_logger.warning("Redis unavailable at %s: %s", url, exc)
        return False


def _configure_caches():
    if not REDIS_URL or not USE_REDIS_CACHE:
        if REDIS_URL and not USE_REDIS_CACHE:
            _settings_logger.info(
                "REDIS_URL is set but USE_REDIS_CACHE=True; using LocMemCache."
            )
        return _LOC_MEM_CACHES

    if not _redis_is_reachable(REDIS_URL):
        if REDIS_REQUIRED:
            raise RuntimeError(
                f"REDIS_REQUIRED=True but Redis is unreachable at {REDIS_URL}. "
                "Start Redis or unset REDIS_REQUIRED for fallback."
            )
        _settings_logger.warning(
            "Redis unreachable; falling back to LocMemCache. "
            "Rate limits will be per-process only."
        )
        return _LOC_MEM_CACHES

    return {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
                # ssl_cert_reqs is only valid for TLS (rediss://) connections;
                # passing it on redis:// raises TypeError on every cache call.
                "CONNECTION_POOL_KWARGS": (
                    {"ssl_cert_reqs": config("REDIS_SSL_CERT_REQS", default="required")}
                    if REDIS_URL.startswith("rediss://")
                    else {}
                ),
            },
        }
    }


CACHES = _configure_caches()

if CACHES["default"]["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache":
    # LocMem is valid for local dev; ratelimit prefers a shared cache in production.
    SILENCED_SYSTEM_CHECKS = [
        "django_ratelimit.E003",
        "django_ratelimit.W001",
    ]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
}

# JSON API only (no file uploads are accepted): cap request bodies.
DATA_UPLOAD_MAX_MEMORY_SIZE = config("DATA_UPLOAD_MAX_MEMORY_SIZE", default=256 * 1024, cast=int)

# -----------------------------------------------------------------------------
# Only used by the Django admin site (cookie sessions); the API uses tokens.
CSRF_TRUSTED_ORIGINS = [o.strip() for o in config("CSRF_TRUSTED_ORIGINS", default="").split(",") if o.strip()]

# -----------------------------------------------------------------------------
# Exam client hardening (Android)
# -----------------------------------------------------------------------------
# Candidate exam endpoints require a registered, approved device.
DEVICE_REQUIRED_FOR_EXAMS = config("DEVICE_REQUIRED_FOR_EXAMS", default=True, cast=bool)
# Require a passing Play Integrity verdict at exam start.
INTEGRITY_REQUIRED = config("INTEGRITY_REQUIRED", default=False, cast=bool)
PLAY_INTEGRITY_PACKAGE = config("PLAY_INTEGRITY_PACKAGE", default="")
GOOGLE_SERVICE_ACCOUNT_FILE = config("GOOGLE_SERVICE_ACCOUNT_FILE", default="")
# Requests carrying X-Client: android with an older X-App-Version get 426.
MIN_ANDROID_APP_VERSION = config("MIN_ANDROID_APP_VERSION", default=1, cast=int)
# Server-side heartbeat gap that counts as a (soft) violation.
HEARTBEAT_GAP_SECONDS = config("HEARTBEAT_GAP_SECONDS", default=25, cast=int)
# Network grace for a final submit that arrives just after the deadline.
SUBMIT_GRACE_SECONDS = config("SUBMIT_GRACE_SECONDS", default=10, cast=int)
# Lifetime of the exam-start challenge nonce.
START_CHALLENGE_TTL_SECONDS = config("START_CHALLENGE_TTL_SECONDS", default=120, cast=int)
MAX_SHORT_ANSWER_LENGTH = config("MAX_SHORT_ANSWER_LENGTH", default=5000, cast=int)

EMAIL_PROVIDER = config('EMAIL_PROVIDER', default='console').strip().lower()
BREVO_API_KEY = config('BREVO_API_KEY', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@parallaxlane.com')
EMAIL_FROM_NAME = config('EMAIL_FROM_NAME', default='ParallaxLane')
EMAIL_PROVIDER_TIMEOUT = config('EMAIL_PROVIDER_TIMEOUT', default=10, cast=int)

if EMAIL_PROVIDER not in {'console', 'brevo'}:
    raise ImproperlyConfigured('EMAIL_PROVIDER must be either console or brevo.')
if EMAIL_PROVIDER == 'console' and not DEBUG and not TESTING:
    raise ImproperlyConfigured(
        'EMAIL_PROVIDER=console would write OTPs to logs; use brevo in production.'
    )
if EMAIL_PROVIDER == 'brevo' and not BREVO_API_KEY and not TESTING:
    raise ImproperlyConfigured(
        'BREVO_API_KEY is required when EMAIL_PROVIDER=brevo.'
    )

EMAIL_BACKEND = (
    'django.core.mail.backends.console.EmailBackend'
    if EMAIL_PROVIDER == 'console'
    else 'django.core.mail.backends.dummy.EmailBackend'
)

OTP_MAX_VERIFY_ATTEMPTS = config('OTP_MAX_VERIFY_ATTEMPTS', default=5, cast=int)
OTP_LOCKOUT_SECONDS = config('OTP_LOCKOUT_SECONDS', default=900, cast=int)
OTP_VERIFY_WINDOW_SECONDS = config('OTP_VERIFY_WINDOW_SECONDS', default=300, cast=int)

if not DEBUG and not TESTING:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    if SECRET_KEY == _INSECURE_SECRET_DEFAULT or len(SECRET_KEY) < 50:
        raise ImproperlyConfigured(
            'SECRET_KEY must be set to a unique value of at least 50 characters in production.'
        )

    if CORS_ALLOW_ALL_ORIGINS:
        raise ImproperlyConfigured(
            'CORS_ALLOW_ALL_ORIGINS must be False in production. Set CORS_ALLOWED_ORIGINS explicitly.'
        )

    if ALLOWED_HOSTS == ['*'] or '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            'ALLOWED_HOSTS must list explicit hostnames in production (not *).'
        )
