"""
Django settings for tformance project.

For more information on this file, see
https://docs.djangoproject.com/en/stable/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/stable/ref/settings/
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

import environ
from celery import schedules
from django.utils.translation import gettext_lazy

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# No default - SECRET_KEY must be set via environment variable
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
# Default to False for security - explicitly set DEBUG=True in development
DEBUG = env.bool("DEBUG", default=False)

# SECURITY: Empty default - must explicitly set ALLOWED_HOSTS in all environments
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Trust proxy headers when behind a reverse proxy (Cloudflare Tunnel, nginx, etc.)
# Set USE_X_FORWARDED_HOST=True and SECURE_PROXY_SSL_HEADER=True in .env when using tunnels
if env.bool("USE_X_FORWARDED_HOST", default=False):
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sitemaps",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.forms",
]

# Put your third-party apps here
THIRD_PARTY_APPS = [
    "allauth",  # allauth account/registration management
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.github",
    "channels",
    "django_htmx",
    "django_vite",
    "allauth.mfa",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_api_key",
    "celery_progress",
    "hijack",  # "login as" functionality
    "hijack.contrib.admin",  # hijack buttons in the admin
    "djstripe",  # stripe integration
    "whitenoise.runserver_nostatic",  # whitenoise runserver
    "waffle",
    "health_check",
    "health_check.db",
    "health_check.contrib.celery",
    "health_check.contrib.redis",
    "django_celery_beat",
    "template_partials.apps.SimpleAppConfig",
]

WAGTAIL_APPS = [
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
]

PEGASUS_APPS = [
    "pegasus.apps.examples.apps.PegasusExamplesConfig",
    "pegasus.apps.employees.apps.PegasusEmployeesConfig",
]

# Put your project-specific apps here
PROJECT_APPS = [
    "apps.content",
    "apps.subscriptions.apps.SubscriptionConfig",
    "apps.users.apps.UserConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.api.apps.APIConfig",
    "apps.utils",
    "apps.web",
    "apps.teams.apps.TeamConfig",
    "apps.teams_example.apps.TeamsExampleConfig",
    "apps.metrics.apps.MetricsConfig",
    "apps.integrations.apps.IntegrationsConfig",
    "apps.onboarding.apps.OnboardingConfig",
    "apps.feedback.apps.FeedbackConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PEGASUS_APPS + PROJECT_APPS + WAGTAIL_APPS

if DEBUG:
    # in debug mode, add daphne to the beginning of INSTALLED_APPS to enable async support
    INSTALLED_APPS.insert(0, "daphne")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.utils.middleware.SecurityHeadersMiddleware",  # Custom security headers
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.teams.middleware.TeamsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "hijack.middleware.HijackUserMiddleware",
    "waffle.middleware.WaffleMiddleware",
]


if DEBUG:
    INSTALLED_APPS.append("django_browser_reload")
    MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")

ROOT_URLCONF = "tformance.urls"

# used to disable the cache in dev, but turn it on in production.
# more here: https://nickjanetakis.com/blog/django-4-1-html-templates-are-cached-by-default-with-debug-true
_LOW_LEVEL_LOADERS = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

# Manually load template partials to allow for easier integration with other templating systems
# like django-cotton.
# https://github.com/carltongibson/django-template-partials?tab=readme-ov-file#advanced-configuration

_DEFAULT_LOADERS = [
    (
        "template_partials.loader.Loader",
        _LOW_LEVEL_LOADERS,
    ),
]

_CACHED_LOADERS = [
    (
        "template_partials.loader.Loader",
        [
            ("django.template.loaders.cached.Loader", _LOW_LEVEL_LOADERS),
        ],
    ),
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.web.context_processors.project_meta",
                "apps.teams.context_processors.team",
                "apps.teams.context_processors.user_teams",
                # this line can be removed if not using google analytics
                "apps.web.context_processors.google_analytics_id",
            ],
            "loaders": _DEFAULT_LOADERS if DEBUG else _CACHED_LOADERS,
            "builtins": [
                "template_partials.templatetags.partials",
            ],
        },
    },
]

WSGI_APPLICATION = "tformance.wsgi.application"

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

if "DATABASE_URL" in env:
    DATABASES = {"default": env.db()}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DJANGO_DATABASE_NAME", default="tformance"),
            "USER": env("DJANGO_DATABASE_USER", default="postgres"),
            "PASSWORD": env("DJANGO_DATABASE_PASSWORD", default="***"),
            "HOST": env("DJANGO_DATABASE_HOST", default="localhost"),
            "PORT": env("DJANGO_DATABASE_PORT", default="5432"),
        }
    }

# Auth and Login

# Django recommends overriding the user model even if you don"t think you need to because it makes
# future changes much easier.
AUTH_USER_MODEL = "users.CustomUser"
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/"

# Cookie Security - explicitly set secure cookie flags
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"

# CSRF trusted origins for ngrok and other tunnels/proxies
# Set via env: CSRF_TRUSTED_ORIGINS=https://abc123.ngrok-free.app,https://example.com
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Allauth setup

ACCOUNT_ADAPTER = "apps.teams.adapter.AcceptInvitationAdapter"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]

ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False  # don't send "forgot password" emails to unknown accounts
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_UNIQUE_EMAIL = True
# This configures a honeypot field to prevent bots from signing up.
# The ID strikes a balance of "realistic" - to catch bots,
# and "not too common" - to not trip auto-complete in browsers.
# You can change the ID or remove it entirely to disable the honeypot.
ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD = "phone_number_x"
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGIN_BY_CODE_ENABLED = False  # Disabled - using OAuth only (GitHub/Google)
ACCOUNT_USER_DISPLAY = lambda user: user.get_display_name()  # noqa: E731

# Disable rate limits in DEBUG mode for E2E testing (Playwright runs multiple workers)
if DEBUG:
    ACCOUNT_RATE_LIMITS = False  # Disable allauth rate limits (must be False, not {})
    RATELIMIT_ENABLE = False  # Disable django-ratelimit

ACCOUNT_FORMS = {
    "signup": "apps.teams.forms.TeamSignupForm",
}
SOCIALACCOUNT_FORMS = {
    "signup": "apps.users.forms.CustomSocialSignupForm",
}

# User signup configuration: change to "mandatory" to require users to confirm email before signing in.
# or "optional" to send confirmation emails but not require them
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="none")

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

# enable social login
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": [
            {
                "client_id": env("GOOGLE_CLIENT_ID", default=""),
                "secret": env("GOOGLE_SECRET_ID", default=""),
                "key": "",
            },
        ],
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    },
    "github": {
        "APPS": [
            {
                "client_id": env("GITHUB_CLIENT_ID", default=""),
                "secret": env("GITHUB_SECRET_ID", default=""),
                "key": "",
            },
        ],
        "SCOPE": [
            "user",
        ],
    },
}

# For turnstile captchas
TURNSTILE_KEY = env("TURNSTILE_KEY", default=None)
TURNSTILE_SECRET = env("TURNSTILE_SECRET", default=None)

# GitHub OAuth
GITHUB_CLIENT_ID = env("GITHUB_CLIENT_ID", default="")
GITHUB_SECRET_ID = env("GITHUB_SECRET_ID", default="")

# GitHub API Configuration (REST vs GraphQL)
# GraphQL provides 10-50x faster bulk sync but REST is needed for Copilot metrics
GITHUB_API_CONFIG = {
    # Master switch for GraphQL API (8.8x faster, 30x fewer API calls)
    "USE_GRAPHQL": env.bool("GITHUB_USE_GRAPHQL", default=True),
    # Per-operation control (all enabled by default)
    "GRAPHQL_OPERATIONS": {
        "initial_sync": env.bool("GITHUB_GRAPHQL_INITIAL_SYNC", default=True),
        "incremental_sync": env.bool("GITHUB_GRAPHQL_INCREMENTAL_SYNC", default=True),
        "pr_complete_data": env.bool("GITHUB_GRAPHQL_PR_COMPLETE", default=True),
        "member_sync": env.bool("GITHUB_GRAPHQL_MEMBERS", default=True),
    },
    # Fallback to REST on GraphQL errors
    "FALLBACK_TO_REST": env.bool("GITHUB_FALLBACK_REST", default=True),
    # Rate limit threshold - switch to REST when GraphQL points < this
    "GRAPHQL_RATE_LIMIT_THRESHOLD": env.int("GITHUB_GRAPHQL_RATE_LIMIT_THRESHOLD", default=100),
}

# Jira OAuth (Atlassian)
JIRA_CLIENT_ID = env("JIRA_CLIENT_ID", default="")
JIRA_CLIENT_SECRET = env("JIRA_CLIENT_SECRET", default="")

# Slack OAuth
SLACK_CLIENT_ID = env("SLACK_CLIENT_ID", default="")
SLACK_CLIENT_SECRET = env("SLACK_CLIENT_SECRET", default="")
SLACK_SIGNING_SECRET = env("SLACK_SIGNING_SECRET", default="")


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = WAGTAIL_I18N_ENABLED = False

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

STATIC_ROOT = BASE_DIR / "static_root"
STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # swap these to use manifest storage to bust cache when files change
        # note: this may break image references in sass/css files which is why it is not enabled by default
        # "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

USE_S3_MEDIA = env.bool("USE_S3_MEDIA", default=False)
if USE_S3_MEDIA:
    # Media file storage in S3
    # Using this will require configuration of the S3 bucket
    # See https://docs.saaspegasus.com/configuration/#storing-media-files
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="tformance-media")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
    STORAGES["default"] = {
        "BACKEND": "apps.web.storage_backends.PublicMediaStorage",
    }

# Vite Integration
DJANGO_VITE = {
    "default": {
        "dev_mode": env.bool("DJANGO_VITE_DEV_MODE", default=DEBUG),
        "manifest_path": BASE_DIR / "static" / ".vite" / "manifest.json",
    }
}

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field

# future versions of Django will use BigAutoField as the default, but it can result in unwanted library
# migration files being generated, so we stick with AutoField for now.
# change this to BigAutoField if you"re sure you want to use it and aren"t worried about migrations.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Removes deprecation warning for future compatibility.
# see https://adamj.eu/tech/2023/12/07/django-fix-urlfield-assume-scheme-warnings/ for details.
FORMS_URLFIELD_ASSUME_HTTPS = True

# Email setup
# https://github.com/anymail/django-anymail - using Resend.com

SERVER_EMAIL = env("SERVER_EMAIL", default="noreply@ianchuk.com")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="tformance <noreply@ianchuk.com>")

# Development: console backend (prints to terminal)
# Production: anymail.backends.resend.EmailBackend
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")

# Resend.com configuration
ANYMAIL = {
    "RESEND_API_KEY": env("RESEND_API_KEY", default=None),
}

EMAIL_SUBJECT_PREFIX = "[tformance] "

# Django sites

SITE_ID = 1

# DRF config
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ("apps.api.permissions.IsAuthenticatedOrHasUserAPIKey",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
}


SPECTACULAR_SETTINGS = {
    "TITLE": "tformance",
    "DESCRIPTION": "The most amazing SaaS application the world has ever seen",  # noqa: E501
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "displayOperationId": True,
    },
    "PREPROCESSING_HOOKS": [
        "apps.api.schema.filter_schema_apis",
    ],
    "APPEND_COMPONENTS": {
        "securitySchemes": {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "Authorization"}}
    },
    "SECURITY": [
        {
            "ApiKeyAuth": [],
        }
    ],
}
# Redis, cache, and/or Celery setup
if "REDIS_URL" in env:
    REDIS_URL = env("REDIS_URL")
elif "REDIS_TLS_URL" in env:
    REDIS_URL = env("REDIS_TLS_URL")
else:
    REDIS_HOST = env("REDIS_HOST", default="localhost")
    REDIS_PORT = env("REDIS_PORT", default="6379")
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

if REDIS_URL.startswith("rediss"):
    REDIS_URL = f"{REDIS_URL}?ssl_cert_reqs=none"

DUMMY_CACHE = {
    "BACKEND": "django.core.cache.backends.dummy.DummyCache",
}
REDIS_CACHE = {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": REDIS_URL,
}
# Allow enabling Redis cache in development for performance testing
# Set USE_REDIS_CACHE=true in .env to enable caching in DEBUG mode
USE_REDIS_CACHE = env.bool("USE_REDIS_CACHE", default=False)
CACHES = {
    "default": REDIS_CACHE if (USE_REDIS_CACHE or not DEBUG) else DUMMY_CACHE,
}

CELERY_BROKER_URL = CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# Run tasks synchronously in tests (no broker needed)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)

# Add tasks to this dict and run `python manage.py bootstrap_celery_tasks` to create them
SCHEDULED_TASKS = {
    "test-celerybeat": {
        "task": "pegasus.apps.examples.tasks.example_log_task",
        "schedule": 60,
        "expire_seconds": 60,
    },
    "sync-subscriptions-every-day": {
        "task": "apps.subscriptions.tasks.sync_subscriptions_task",
        "schedule": timedelta(days=1),
        "expire_seconds": 60 * 60,
    },
    "sync-github-repositories-daily": {
        "task": "apps.integrations.tasks.sync_all_repositories_task",
        "schedule": schedules.crontab(minute=0, hour=4),  # 4 AM UTC
        "expire_seconds": 60 * 60 * 4,  # 4 hour expiry
    },
    "sync-github-members-daily": {
        "task": "apps.integrations.tasks.sync_all_github_members_task",
        "schedule": schedules.crontab(minute=15, hour=4),  # 4:15 AM UTC (after repos)
        "expire_seconds": 60 * 60,  # 1 hour expiry
    },
    "sync-jira-projects-daily": {
        "task": "apps.integrations.tasks.sync_all_jira_projects_task",
        "schedule": schedules.crontab(minute=30, hour=4),  # 4:30 AM UTC (after GitHub)
        "expire_seconds": 60 * 60 * 4,  # 4 hour expiry
    },
    "check-leaderboards-hourly": {
        "task": "apps.integrations.tasks.post_weekly_leaderboards_task",
        "schedule": schedules.crontab(minute=0),  # Every hour on the hour
        "expire_seconds": 60 * 30,  # 30 minute expiry
    },
    "aggregate-weekly-metrics-monday": {
        "task": "apps.integrations.tasks.aggregate_all_teams_weekly_metrics_task",
        "schedule": schedules.crontab(minute=0, hour=1, day_of_week=1),  # Monday 1 AM UTC
        "expire_seconds": 60 * 60 * 2,  # 2 hour expiry
    },
    "compute-daily-insights": {
        "task": "apps.metrics.tasks.compute_all_team_insights",
        "schedule": schedules.crontab(minute=0, hour=6),  # 6 AM UTC (after data syncs)
        "expire_seconds": 60 * 60,  # 1 hour expiry
    },
}

# Channels / Daphne setup

ASGI_APPLICATION = "tformance.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# Health Checks
# A list of tokens that can be used to access the health check endpoint
HEALTH_CHECK_TOKENS = env.list("HEALTH_CHECK_TOKENS", default="")

# Wagtail config

WAGTAIL_SITE_NAME = "tformance Content"
WAGTAILADMIN_BASE_URL = "http://localhost:8000"

# Waffle config

WAFFLE_FLAG_MODEL = "teams.Flag"

# Pegasus config

# replace any values below with specifics for your project
PROJECT_METADATA = {
    "NAME": gettext_lazy("tformance"),
    "URL": "http://localhost:8000",
    "DESCRIPTION": gettext_lazy("AI Impact Analytics - measure how AI coding tools affect your team's performance"),  # noqa: E501
    "IMAGE": "https://upload.wikimedia.org/wikipedia/commons/2/20/PEO-pegasus_black.svg",
    "KEYWORDS": "SaaS, django",
    "CONTACT_EMAIL": "oleksii.ianchuk@gmail.com",
}

# set this to True in production to have URLs generated with https instead of http
USE_HTTPS_IN_ABSOLUTE_URLS = env.bool("USE_HTTPS_IN_ABSOLUTE_URLS", default=False)

ADMINS = [("Oleksii", "oleksii.ianchuk@gmail.com")]

# Add your google analytics ID to the environment to connect to Google Analytics
GOOGLE_ANALYTICS_ID = env("GOOGLE_ANALYTICS_ID", default="")

# these daisyui themes are used to set the dark and light themes for the site
# they must be valid themes included in your tailwind.config.js file.
# more here: https://daisyui.com/docs/themes/
LIGHT_THEME = "light"
DARK_THEME = "dark"

# Stripe config
# modeled to be the same as https://github.com/dj-stripe/dj-stripe
# Note: don"t edit these values here - edit them in your .env file or environment variables!
# The defaults are provided to prevent crashes if your keys don"t match the expected format.
STRIPE_LIVE_PUBLIC_KEY = env("STRIPE_LIVE_PUBLIC_KEY", default="pk_live_***")
STRIPE_LIVE_SECRET_KEY = env("STRIPE_LIVE_SECRET_KEY", default="sk_live_***")
STRIPE_TEST_PUBLIC_KEY = env("STRIPE_TEST_PUBLIC_KEY", default="pk_test_***")
STRIPE_TEST_SECRET_KEY = env("STRIPE_TEST_SECRET_KEY", default="sk_test_***")
# Change to True in production
STRIPE_LIVE_MODE = env.bool("STRIPE_LIVE_MODE", False)
STRIPE_PRICING_TABLE_ID = env("STRIPE_PRICING_TABLE_ID", default="")

# djstripe settings

DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"  # change to "djstripe_id" if not a new installation
DJSTRIPE_SUBSCRIBER_MODEL = "teams.Team"
DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK = lambda request: request.team  # noqa E731

SILENCED_SYSTEM_CHECKS = [
    "djstripe.I002",  # Pegasus uses the same settings as dj-stripe for keys, so don't complain they are here
]

if "test" in sys.argv:
    # Silence unnecessary warnings in tests
    SILENCED_SYSTEM_CHECKS.append("djstripe.I002")
    # Use fast password hasher for tests (PBKDF2 is intentionally slow for security)
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


# Sentry setup

# populate this to configure sentry. should take the form: "https://****@sentry.io/12345"
SENTRY_DSN = env("SENTRY_DSN", default="")


if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration()])


# PostHog Analytics
# Used for product analytics, feature flags, and LLM observability
POSTHOG_API_KEY = env("POSTHOG_API_KEY", default="")
POSTHOG_HOST = env("POSTHOG_HOST", default="https://us.i.posthog.com")

if POSTHOG_API_KEY:
    import posthog

    posthog.project_api_key = POSTHOG_API_KEY
    posthog.host = POSTHOG_HOST


# Google Gemini AI
# Used for LLM-powered insights in Phase 2
GOOGLE_AI_API_KEY = env("GOOGLE_AI_API_KEY", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": '[{asctime}] {levelname} "{name}" {message}',
            "style": "{",
            "datefmt": "%d/%b/%Y %H:%M:%S",  # match Django server time format
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
        },
        "tformance": {
            "handlers": ["console"],
            "level": env("TFORMANCE_LOG_LEVEL", default="INFO"),
        },
        "pegasus": {
            "handlers": ["console"],
            "level": env("PEGASUS_LOG_LEVEL", default="DEBUG"),
        },
    },
}

# Integration Encryption
# Used to encrypt OAuth tokens and other sensitive integration credentials
# No default - must be set via environment variable (test key is set in conftest.py)
INTEGRATION_ENCRYPTION_KEY = env("INTEGRATION_ENCRYPTION_KEY", default=None)

# Team Data Isolation
# In production, raise an exception if team context is missing when using for_team manager
# In development, allow silent fallback to empty queryset for easier debugging
STRICT_TEAM_CONTEXT = not DEBUG

# Production Security Settings
# These settings are enabled when not in DEBUG mode
if not DEBUG:
    # HSTS (HTTP Strict Transport Security)
    # Forces browsers to use HTTPS for all future requests
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Redirect all HTTP to HTTPS
    SECURE_SSL_REDIRECT = True

    # Ensure cookies are only sent over HTTPS (already set above, but explicit for production)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Prevent session hijacking by only allowing cookies from the same site
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True

    # X-Frame-Options - prevent clickjacking
    X_FRAME_OPTIONS = "DENY"
