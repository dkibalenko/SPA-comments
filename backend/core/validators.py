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
        1. bleach strips everything outside `ALLOWED_TAGS`
        2. `validate_xhtml_closure` checks all remaining tags are closed
    
    :param text: Raw user input.
    :returns: Sanitized, XHTML-valid string safe for storage and display.
    :raises ValidationError: If remaining tags are not properly closed.
    """
    cleaned = bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
        strip_comments=True
    )
    _validate_xhtml_closure(cleaned)
    return cleaned


def _validate_xhtml_closure(text: str) -> None:
    """Verify every opening tag has a matching closing tag.
    
    Uses a stack to track nesting. Raises if any tag is unclosed
    or closed in the wrong order.
    
    :raises ValidationError: If tags are unclosed or misnested.
    """
    opening_tags = OPENING_TAG_RE.findall(text)
    closing_tags = CLOSING_TAG_RE.findall(text)

    if len(opening_tags) != len(closing_tags):
        raise ValidationError(
            "Comment contains unclosed HTML tags. "
            "All tags must be properly closed."
        )

    stack: list[str] = []
    # e.g. input: <p><strong>Hello</strong></p> =>
    # [('', 'p'), ('', 'strong'), ('/', 'strong'), ('/', 'p')]
    tokens = re.findall(r"<(/?)([a-zA-Z]+)[^>]*>", text)

    # check if all tags match
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

    if stack:  # pragma: no cover
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
