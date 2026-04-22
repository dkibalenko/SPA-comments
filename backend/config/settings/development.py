from datetime import timedelta

from .base import *


DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True  # open in dev only

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}
