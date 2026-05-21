import base64
import uuid

import pytest


CAPTCHA_URL = "/api/captcha/"


@pytest.mark.django_db
class TestCaptchaGenerate:

    def test_returns_200(self, api_client, use_local_memory_cache):
        """
        The endpoint should always return 200, even if the captcha generation
        logic fails (e.g. due to Redis being unavailable).
        """
        resp = api_client.get(CAPTCHA_URL)
        assert resp.status_code == 200

    def test_response_contains_token_and_image(self, api_client, use_local_memory_cache):
        """Tests that the response includes a token and a base64-encoded image string."""
        resp = api_client.get(CAPTCHA_URL)
        assert "token" in resp.data
        assert "image" in resp.data

    def test_token_is_valid_uuid(self, api_client, use_local_memory_cache):
        """Tests that the token in the response is a valid UUID string.

        Raises ValueError if the token is not a valid UUID.
        """
        resp = api_client.get(CAPTCHA_URL)
        uuid.UUID(resp.data["token"])  # raises ValueError if not a valid UUID

    def test_image_is_valid_base64_encoded_png(self, api_client, use_local_memory_cache):
        """Tests that the image in the response is a valid base64-encoded PNG."""
        resp = api_client.get(CAPTCHA_URL)
        decoded = base64.b64decode(resp.data["image"])
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_successive_calls_return_different_tokens(self, api_client, use_local_memory_cache):
        """Tests that successive calls to the endpoint return different tokens."""
        token1 = api_client.get(CAPTCHA_URL).data["token"]
        token2 = api_client.get(CAPTCHA_URL).data["token"]
        assert token1 != token2
