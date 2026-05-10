import base64
import uuid
from unittest.mock import patch

import pytest

from apps.captcha_app.services import (
    CAPTCHA_CHARS,
    CAPTCHA_KEY_PREFIX,
    CAPTCHA_LENGTH,
    CAPTCHA_TTL,
    CaptchaService,
)
from core.exceptions import CaptchaError


# CaptchaService.validate

class TestCaptchaServiceValidate:

    def test_correct_answer_passes(self):
        """Matching answer (case-insensitive) must not raise."""
        with patch("django.core.cache.cache.get", return_value = "abcdef"), \
             patch("django.core.cache.cache.delete"):
            CaptchaService().validate(token = "tok", answer = "ABCDEF")  # must not raise

    def test_expired_or_missing_token_raises(self):
        """cache.get returning None means the token is expired or never existed."""
        with patch("django.core.cache.cache.get", return_value = None), \
             patch("django.core.cache.cache.delete"):
            with pytest.raises(CaptchaError, match = "expired"):
                CaptchaService().validate(token = "bad-tok", answer = "anything")

    def test_wrong_answer_raises(self):
        """A token that exists but the answer doesn't match must raise."""
        with patch("django.core.cache.cache.get", return_value = "correct"), \
             patch("django.core.cache.cache.delete"):
            with pytest.raises(CaptchaError, match = "Incorrect"):
                CaptchaService().validate(token = "tok", answer = "wrong")

    def test_cache_key_deleted_on_correct_answer(self):
        """Key is consumed even when the answer is correct — one-time use."""
        with patch("django.core.cache.cache.get", return_value = "abc123"), \
             patch("django.core.cache.cache.delete") as mock_delete:
            CaptchaService().validate(token = "tok", answer = "abc123")

        mock_delete.assert_called_once_with(f"{CAPTCHA_KEY_PREFIX}tok")

    def test_cache_key_deleted_on_wrong_answer(self):
        """Key must be deleted even when the answer is wrong — prevents brute-force."""
        with patch("django.core.cache.cache.get", return_value = "abc123"), \
             patch("django.core.cache.cache.delete") as mock_delete:
            with pytest.raises(CaptchaError):
                CaptchaService().validate(token = "tok", answer = "wrong")

        mock_delete.assert_called_once_with(f"{CAPTCHA_KEY_PREFIX}tok")

    def test_answer_comparison_is_case_insensitive(self):
        """Stored answer is lowercased at generation; validation must also lowercase."""
        with patch("django.core.cache.cache.get", return_value = "abc123"), \
             patch("django.core.cache.cache.delete"):
            CaptchaService().validate(token = "tok", answer = "ABC123")  # must not raise

    def test_answer_whitespace_is_stripped(self):
        """Leading/trailing whitespace in user input must not cause failure."""
        with patch("django.core.cache.cache.get", return_value = "abc123"), \
             patch("django.core.cache.cache.delete"):
            CaptchaService().validate(token = "tok", answer = "  abc123  ")  # must not raise


# CaptchaService._random_text

class TestCaptchaServiceRandomText:

    def test_returns_string_of_correct_length(self):
        """Generated text must be exactly CAPTCHA_LENGTH chars long."""
        assert len(CaptchaService._random_text()) == CAPTCHA_LENGTH

    def test_all_characters_from_allowed_set(self):
        """Every character in the generated text must be from CAPTCHA_CHARS."""
        assert all(c in CAPTCHA_CHARS for c in CaptchaService._random_text())

    def test_successive_calls_produce_different_values(self):
        """Multiple calls should produce different random strings."""
        # collision probability is negligible
        assert CaptchaService._random_text() != CaptchaService._random_text()


# CaptchaService._render_image

class TestCaptchaServiceRenderImage:

    def test_returns_non_empty_string(self):
        """Rendered image must be a non-empty base64 string."""
        assert len(CaptchaService._render_image("ABC123")) > 0

    def test_result_is_valid_base64(self):
        """Result must be valid base64-encoded data."""
        result = CaptchaService._render_image("ABC123")
        # b64decode raises binascii.Error if the string is not valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_decoded_result_is_png(self):
        """Decoded image data must start with PNG signature bytes."""
        result = CaptchaService._render_image("ABC123")
        decoded = base64.b64decode(result)
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"


# CaptchaService.generate

class TestCaptchaServiceGenerate:

    def test_returns_token_and_image_keys(self):
        """Result must contain 'token' and 'image' keys."""
        with patch("django.core.cache.cache.set"):
            result = CaptchaService().generate()
        assert "token" in result
        assert "image" in result

    def test_token_is_valid_uuid(self):
        """Generated token must be a valid UUID string."""
        with patch("django.core.cache.cache.set"):
            result = CaptchaService().generate()
        uuid.UUID(result["token"])  # raises ValueError if not a valid UUID

    def test_image_is_valid_base64_encoded_png(self):
        """Generated image must be a base64-encoded PNG."""
        with patch("django.core.cache.cache.set"):
            result = CaptchaService().generate()
        decoded = base64.b64decode(result["image"])
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_answer_stored_in_cache_lowercased(self):
        """Answer stored in cache must be lowercased for case-insensitive validation."""
        with patch("django.core.cache.cache.set") as mock_set:
            CaptchaService().generate()
        stored_answer = mock_set.call_args.args[1]
        assert stored_answer == stored_answer.lower()

    def test_cache_key_uses_token_and_correct_prefix(self):
        """Cache key must be in the format 'captcha:{token}'."""
        with patch("django.core.cache.cache.set") as mock_set:
            result = CaptchaService().generate()
        cache_key = mock_set.call_args.args[0]
        assert cache_key == f"{CAPTCHA_KEY_PREFIX}{result['token']}"

    def test_cache_stored_with_correct_ttl(self):
        """Cache set call must include the correct TTL for expiration."""
        with patch("django.core.cache.cache.set") as mock_set:
            CaptchaService().generate()
        assert mock_set.call_args.kwargs["timeout"] == CAPTCHA_TTL
