"""Random data generators and shared HTTP helpers for load test users."""

import random
import string


# Random user identity


def random_username() -> str:
    """Alphanumeric username (5-12 chars). Satisfies [a-zA-Z0-9]+ validation"""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k = random.randint(5, 12)))


def random_email(username: str) -> str:
    return f"{username}@loadtest.example"


# Comment content

_TEXTS = [
    "This is a well-thought-out comment about the topic at hand.",
    "I strongly agree with the points raised here.",
    "Could you elaborate on this? I find it quite interesting.",
    "Great perspective, thanks for sharing.",
    "Has anyone else noticed this pattern before?",
    "<strong>Important point:</strong> this deserves more attention.",
    "I have a different take: <i>the evidence suggests otherwise</i>.",
    "Interesting discussion. I would add that context matters a lot here.",
    "Thanks for the clear explanation.",
    "<code>print('hello')</code> - a classic starting point.",
]

_ORDERINGS = ["-date", "date", "username", "-username", "email", "-email"]


def random_text() -> str:
    return random.choice(_TEXTS)


def random_ordering() -> str:
    return random.choice(_ORDERINGS)


# Captcha


def get_captcha(client) -> tuple[str | None, str | None]:
    """GET `/api/captcha/` and return (token, answer).

    `debug_answer` is only present in the response when the Django server
    runs with DEBUG = True. Returns (None, None) on any failure - callers
    skip their task gracefully instead of crashing.
    """
    resp = client.get("/api/captcha/", name="/api/captcha/")
    if resp.status_code != 200:
        return None, None
    data = resp.json()
    return data.get("token"), data.get("debug_answer")
