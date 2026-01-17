# flake8: noqa: F405
from .settings import *  # noqa F401

# Note: it is recommended to use the "DEBUG" environment variable to override this value in your main settings.py file.
# A future release may remove it from here.
DEBUG = False

# fix ssl mixed content issues
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Django security checklist settings.
# More details here: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
# SECURE_SSL_REDIRECT can be disabled for environments behind a proxy that handles SSL (e.g., Cloudflare Tunnel)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTP Strict Transport Security settings
# https://docs.djangoproject.com/en/stable/ref/middleware/#http-strict-transport-security
# Start with 1 year (31536000 seconds) - standard production value
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

USE_HTTPS_IN_ABSOLUTE_URLS = True

# If you don't want to use environment variables to set production hosts you can add them here
# ALLOWED_HOSTS = ["example.com"]

# Your email config goes here.
# see https://github.com/anymail/django-anymail for more details / examples
# To use mailgun, uncomment the lines below and make sure your key and domain
# are available in the environment.
# EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

# ANYMAIL = {
#     "MAILGUN_API_KEY": env("MAILGUN_API_KEY", default=None),
#     "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN", default=None),
# }

ADMINS = [
    ("Oleksii", "oleksii.ianchuk@gmail.com"),
]
