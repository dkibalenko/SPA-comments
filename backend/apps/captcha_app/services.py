import base64
import random
import string
import uuid
from io import BytesIO

from captcha.image import ImageCaptcha
from django.conf import settings
from django.core.cache import cache

from core.exceptions import CaptchaError

CAPTCHA_LENGTH = 6
CAPTCHA_TTL = 300
CAPTCHA_KEY_PREFIX = "captcha:"
CAPTCHA_CHARS = string.ascii_letters + string.digits


class CaptchaService:
    """Generates and validates image CAPTCHAs backed by Redis.

    Flow:
        1. `generate()` → stores answer in Redis, returns token + image
        2. Client submits token + typed answer with comment form
        3. `validate()` → pops key from Redis, compares answer
        4. Key is deleted regardless of outcome (one-time use)
    """

    def generate(self) -> dict:
        """Generate a new CAPTCHA challenge.

        :returns: {
            "token": str UUID - send back with form submission,
            "image": str base64 PNG - render as
                <img src="data:image/png;base64,...">
        }
        """
        answer = self._random_text()
        token = str(uuid.uuid4())
        cache_key = f"{CAPTCHA_KEY_PREFIX}{token}"

        cache.set(cache_key, answer.lower(), timeout=CAPTCHA_TTL)

        image_b64 = self._render_image(answer)

        result = {"token": token, "image": image_b64}

        if settings.DEBUG:
            result["debug_answer"] = answer

        return result

    def validate(self, token: str, answer: str) -> None:
        """Validate a CAPTCHA response and consume the token.

        Always deletes the Redis key - even on failure.
        This prevents brute-forcing the same token repeatedly.

        :param token: UUID returned by generate().
        :param answer: Text typed by the user.
        :raises CaptchaError: If token is expired, invalid, or answer is wrong.
        """
        cache_key = f"{CAPTCHA_KEY_PREFIX}{token}"

        stored_answer = cache.get(cache_key)

        cache.delete(cache_key)

        if stored_answer is None:
            raise CaptchaError(
                "CAPTCHA expired or invalid token. Please request a new one."
            )

        if answer.lower().strip() != stored_answer:
            raise CaptchaError("Incorrect CAPTCHA answer. Please try again.")

    @staticmethod
    def _random_text() -> str:
        """Generate a random alphanumeric string of CAPTCHA_LENGTH chars."""
        return "".join(random.choices(CAPTCHA_CHARS, k=CAPTCHA_LENGTH))

    @staticmethod
    def _render_image(text: str) -> str:
        """Render text to a PNG image and return as base64 string.

        Uses the `captcha` library which wraps Pillow.
        Returns a data-URI-ready base64 string.
        """
        generator = ImageCaptcha(width=200, height=60)
        image_data: BytesIO = generator.generate(text)
        return base64.b64encode(image_data.read()).decode("utf-8")
