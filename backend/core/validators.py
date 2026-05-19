import re

import bleach

from core.exceptions import ValidationError

ALLOWED_TAGS: list[str] = ["a", "code", "i", "strong"]
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {"a": ["href", "title"]}
USERNAME_RE = re.compile(r"^[a-zA-Z0-9]+$")
OPENING_TAG_RE = re.compile(r"<(?P<tag>[a-zA-Z]+)(?:\s[^>]*)?>")
CLOSING_TAG_RE = re.compile(r"</(?P<tag>[a-zA-Z]+)>")


def sanitize_comment_text(text: str) -> str:
    """Strip disallowed HTML tags and validate XHTML tag closure.

    Pipeline:
        1. `_validate_xhtml_closure` checks allowed tags are closed in raw input
           (before bleach, which would auto-close unclosed tags and hide the error)
        2. bleach strips everything outside `ALLOWED_TAGS`

    :param text: Raw user input.
    :returns: Sanitized, XHTML-valid string safe for storage and display.
    :raises ValidationError: If remaining tags are not properly closed.
    """
    _validate_xhtml_closure(text, only_tags=ALLOWED_TAGS)
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
        strip_comments=True,
    )


def _validate_xhtml_closure(text: str, only_tags: list[str] | None = None) -> None:
    """Verify every opening tag has a matching closing tag.

    Uses a stack to track nesting. When `only_tags` is given, skips any tag
    not in that set - this allows to validate raw input before bleach strips
    disallowed tags, without raising on tags bleach will remove anyway.

    :raises ValidationError: If tags are unclosed or misnested.
    """
    # e.g. input: <p><strong>Hello</strong></p> =>
    # [('', 'p'), ('', 'strong'), ('/', 'strong'), ('/', 'p')]
    tokens = re.findall(r"<(/?)([a-zA-Z]+)[^>]*>", text)
    if only_tags:
        tokens = [(c, t) for c, t in tokens if t.lower() in only_tags]

    stack: list[str] = []
    for is_closing, tag in tokens:
        tag = tag.lower()
        if not is_closing:
            stack.append(tag)
        else:
            if not stack or stack[-1] != tag:
                raise ValidationError(
                    f"Misnested or unexpected closing tag: </{tag}>. "
                    "Tags must be closed in reverse order of opening."
                )
            stack.pop()

    if stack:
        raise ValidationError(
            f"Unclosed tag(s): {', '.join(f'<{t}>' for t in stack)}."
        )


def validate_username(value: str) -> str:
    """Ensure username contains only [a-zA-Z0-9].

    :raises ValidationError: If the value contains invalid characters.
    """
    if not USERNAME_RE.match(value):
        raise ValidationError(
            "Username may only contain letters and digits (a-zA-Z0-9)."
        )
    return value
