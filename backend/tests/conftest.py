import uuid

import pytest
from unittest.mock import patch
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def bypass_captcha():
    """Silence CaptchaService.validate for tests that don't exercise captcha logic."""
    with patch("apps.captcha_app.services.CaptchaService.validate"):
        yield


@pytest.fixture
def use_local_memory_cache():
    """Replace Redis with an in-process locmem cache for the duration of the test.

    Safe for tests that exercise cache.get / cache.set paths via Django's cache
    abstraction. Does NOT affect invalidate_list_cache() which calls
    get_redis_connection() directly — avoid this fixture in tests that trigger
    top-level comment creation.
    """
    with override_settings(
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": str(uuid.uuid4()),  # called each time the fixture runs - every test gets its own slot in _caches
            }
        }
    ):
        yield
