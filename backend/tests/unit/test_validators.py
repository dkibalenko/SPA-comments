import pytest

from core.exceptions import ValidationError
from core.validators import (
    _validate_xhtml_closure,
    sanitize_comment_text,
    validate_username,
)


# sanitize_comment_text

class TestSanitizeCommentText:
    """Tests for the full sanitization pipeline: bleach clean → XHTML check."""

    @pytest.mark.parametrize(
        "raw, expected", 
        [
            ("<strong>Bold</strong>", "<strong>Bold</strong>"),
            ("<i>Italic</i>", "<i>Italic</i>"),
            ("<code>code()</code>", "<code>code()</code>"),
            ("<strong><i>nested</i></strong>", "<strong><i>nested</i></strong>"),
            ("Hello world", "Hello world"),
            # href and title are in ALLOWED_ATTRIBUTES["a"]
            (
                '<a href="http://x.com" title="X">link</a>',
                '<a href="http://x.com" title="X">link</a>',
            ),
        ]
    )
    def test_preserves_allowed_content(self, raw, expected):
        assert sanitize_comment_text(raw) == expected

    @pytest.mark.parametrize(
        "raw, forbidden",
        [
            # disallowed tag markup must not appear in output
            ("<script>evil()</script>text", "<script>"),
            ("<p>paragraph</p>", "<p>"),
            ("<div>block</div>", "<div>"),
            ("<img src='x' onerror='bad()'>", "<img"),
            # disallowed attribute on an allowed tag must be stripped
            ('<strong onclick="bad()">text</strong>', "onclick"),
            # disallowed attribute mixed with allowed tag
            ('<a href="http://ok.com" onmouseover="bad()">lnk</a>', "onmouseover"),
        ]
    )
    def test_strips_disallowed_markup(self, raw, forbidden):
        result = sanitize_comment_text(raw)
        assert forbidden not in result

    def test_javascript_uri_not_executable(self):
        result = sanitize_comment_text('<a href="javascript:alert(1)">click</a>')
        assert "javascript:" not in result

    def test_empty_string_returns_empty(self):
        assert sanitize_comment_text("") == ""

    def test_siblings_both_preserved(self):
        raw = "<strong>a</strong><i>b</i>"
        assert sanitize_comment_text(raw) == "<strong>a</strong><i>b</i>"

    def test_bleach_auto_closes_unclosed_allowed_tag(self):
        # bleach's html5lib parser normalizes malformed HTML before
        # _validate_xhtml_closure runs — unclosed tags are auto-closed.
        result = sanitize_comment_text("<strong>unclosed")
        assert result == "<strong>unclosed</strong>"

    def test_bleach_fixes_misnested_allowed_tags(self):
        # html5lib re-orders misnested tags to produce valid HTML,
        # so _validate_xhtml_closure never sees the bad input.
        result = sanitize_comment_text("<strong><i>text</strong></i>")
        assert result == "<strong><i>text</i></strong>"

    def test_html_comment_stripped(self):
        result = sanitize_comment_text("<!-- secret -->visible")
        assert "<!--" not in result
        assert "visible" in result


# _validate_xhtml_closure

class TestValidateXhtmlClosure:
    """Tests for the XHTML tag-closure validator in isolation."""

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "plain text without any tags",
            "<strong>closed</strong>",
            "<i>italic</i>",
            "<code>snippet</code>",
            '<a href="http://x.com">link</a>',
            "<strong><i>properly nested</i></strong>",
            "<strong>a</strong><i>b</i>",  # siblings
            "<code><i>deep</i></code>",
        ]
    )
    def test_valid_xhtml_passes(self, text):
        _validate_xhtml_closure(text)  # must not raise

    @pytest.mark.parametrize(
        "text",
        [
            "<strong>not closed",
            "<i>unclosed <code>inner</code>",    # outer tag left open
            "<strong><i>misnested</strong></i>", # wrong close order
            "</strong>",                         # closing with no opening
        ]
    )
    def test_invalid_xhtml_raises(self, text):
        with pytest.raises(ValidationError):
            _validate_xhtml_closure(text)

    def test_unclosed_error_message(self):
        with pytest.raises(ValidationError, match="unclosed"):
            _validate_xhtml_closure("<strong>no closing tag")

    def test_misnested_error_message(self):
        with pytest.raises(ValidationError, match="Misnested"):
            _validate_xhtml_closure("<strong><i>text</strong></i>")

    def test_unclosed_inner_tag_error_message(self):
        # outer closed correctly, but inner <i> is not
        with pytest.raises(ValidationError, match="unclosed"):
            _validate_xhtml_closure("<strong><i>text</strong>")


# validate_username

class TestValidateUsername:
    """Tests for the alphanumeric-only username validator."""

    @pytest.mark.parametrize(
        "username",
        [
            "alice",
            "Bob",
            "User123",
            "ABC",
            "123",
            "a1B2c3",
            "ALLCAPS",
            "a",          # single char
        ]
    )
    def test_valid_username_returned_unchanged(self, username):
        assert validate_username(username) == username

    @pytest.mark.parametrize(
        "username",
        [  # Each case represents a realistic mistake or injection attempt
            "",            # empty — regex requires at least one char
            "user_name",   # underscore
            "user name",   # space
            "user@dom",    # at-sign
            "héllo",       # non-ASCII
            "user!",       # exclamation mark
            "user-1",      # hyphen
            "user.name",   # dot
        ]
    )
    def test_invalid_username_raises(self, username):
        with pytest.raises(ValidationError):
            validate_username(username)
