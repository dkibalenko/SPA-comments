from unittest.mock import patch

import pytest

from apps.notifications.emails import ReplyNotificationData, send_reply_notification


def _make_data(**overrides):
    """Helper to build ReplyNotificationData with sensible defaults, overridden by caller."""
    defaults = dict(
        recipient_email = "parent@example.com",
        recipient_username = "parent_user",
        reply_author = "reply_user",
        parent_text = "Original comment text",
        reply_text = "Reply text here",
        comment_id = "comment-uuid-123",
    )
    defaults.update(overrides)
    return ReplyNotificationData(**defaults)


class TestSendReplyNotification:

    def test_send_mail_called_once(self):
        """Verify that send_mail is called exactly once per notification."""
        with patch("apps.notifications.emails.send_mail") as mock_send:
            send_reply_notification(_make_data())
        mock_send.assert_called_once()

    def test_correct_recipient(self):
        """Verify that the recipient email is correctly passed to send_mail."""
        with patch("apps.notifications.emails.send_mail") as mock_send:
            send_reply_notification(_make_data(recipient_email = "target@example.com"))
        _, kwargs = mock_send.call_args
        assert "target@example.com" in mock_send.call_args[1]["recipient_list"]

    def test_subject_is_string(self):
        """Verify that the email subject is a non-empty string."""
        with patch("apps.notifications.emails.send_mail") as mock_send:
            send_reply_notification(_make_data())
        subject = mock_send.call_args[1]["subject"]
        assert isinstance(subject, str)
        assert len(subject) > 0

    def test_message_contains_recipient_username(self):
        """Verify that the email message includes the recipient's username."""
        with patch("apps.notifications.emails.send_mail") as mock_send:
            send_reply_notification(_make_data(recipient_username = "bob"))
        message = mock_send.call_args[1]["message"]
        assert "bob" in message

    def test_message_contains_reply_author(self):
        """Verify that the email message includes the reply author's username."""
        with patch("apps.notifications.emails.send_mail") as mock_send:
            send_reply_notification(_make_data(reply_author = "alice"))
        message = mock_send.call_args[1]["message"]
        assert "alice" in message

    def test_send_mail_failure_reraises(self):
        """Verify that exceptions from send_mail are not swallowed."""
        with patch(
            "apps.notifications.emails.send_mail",
            side_effect = Exception("SMTP error"),
        ):
            with pytest.raises(Exception, match = "SMTP error"):
                send_reply_notification(_make_data())
