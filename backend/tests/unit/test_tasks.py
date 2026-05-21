from unittest.mock import MagicMock, patch

import pytest

from apps.notifications.tasks import notify_reply_author


def _make_reply(parent = True, self_reply = False) -> MagicMock:
    """Build a mock Comment representing a reply.

    :param parent: If False, the reply will have no parent (edge case).
    :param self_reply: If True, the reply's author is the same as the parent's (edge case).
    :return: A MagicMock simulating a Comment instance with the specified conditions.
    """
    reply = MagicMock()
    reply.id = "reply-uuid"
    reply.text = "Reply text"
    reply.user_id = "user-a"
    reply.user.username = "alice"

    if parent:
        reply.parent = MagicMock()
        reply.parent.text = "Parent text"
        reply.parent.user_id = "user-a" if self_reply else "user-b"
        reply.parent.user.email = "bob@example.com"
        reply.parent.user.username = "bob"
    else:
        reply.parent = None

    return reply


def _run_task(comment_id, mock_reply) -> MagicMock:
    """Run the task function directly, bypassing Celery machinery.

    Each `.` in the queryset chain is a new attribute access on the previous MagicMock.
    Setting `.return_value` at the end pins what `.get()` returns.

    Calling `.run(comment_id)` instead of calling the task normally: `notify_reply_author.run(...)`
    calls the task function directly, completely bypassing the Celery broker, worker queue, and serialization.
    The task runs synchronously in the test process.

    :param comment_id: The UUID string to pass to the task.
    :param mock_reply: The MagicMock to return from the queryset's `.get()`.
    :return: The mock for `send_reply_notification` to allow assertions on how it was called.
    """
    with patch("apps.comments.models.Comment") as MockComment:
        MockComment.objects.select_related.return_value.get.return_value = mock_reply
        with patch("apps.notifications.tasks.send_reply_notification") as mock_send:
            notify_reply_author.run(comment_id)
    return mock_send


class TestNotifyReplyAuthor:

    def test_normal_reply_sends_notification(self):
        """Test that a normal reply triggers a notification with correct data."""
        mock_send = _run_task("reply-uuid", _make_reply())
        mock_send.assert_called_once()

    def test_notification_data_has_correct_recipient(self):
        """Test that the notification data contains the correct recipient email and username.

        The test verifies the recipient is the parent author, not the replier.
        Sending to the wrong recipient would be a critical bug.
        """
        mock_send = _run_task("reply-uuid", _make_reply())
        data = mock_send.call_args[0][0]
        assert data.recipient_email == "bob@example.com"
        assert data.recipient_username == "bob"

    def test_notification_data_has_correct_authors_and_texts(self):
        """Test that the notification data contains the correct reply author, parent text, and reply text."""
        mock_send = _run_task("reply-uuid", _make_reply())
        data = mock_send.call_args[0][0]
        assert data.reply_author == "alice"
        assert data.parent_text == "Parent text"
        assert data.reply_text == "Reply text"

    def test_no_parent_skips_notification(self):
        """Test that if the comment has no parent, no notification is sent."""
        mock_send = _run_task("reply-uuid", _make_reply(parent = False))
        mock_send.assert_not_called()

    def test_self_reply_skips_notification(self):
        """Test that if the reply is from the same user as the parent, no notification is sent."""
        mock_send = _run_task("reply-uuid", _make_reply(self_reply = True))
        mock_send.assert_not_called()

    def test_send_failure_triggers_retry(self):
        """Test that if sending the notification raises an exception, the task retries.
        This simulates a transient failure (e.g., SMTP server down) and verifies that the retry mechanism is invoked.

        `self.retry()` is a Celery method on the bound task instance.
        `patch.object` replaces it on the actual task object (not on a module path).
        Its `side_effect` raises `Exception("retry called")` - this is the only way to observe that `retry` was called,
        because in a real Celery worker `self.retry()` raises `celery.exceptions.Retry` to signal the worker to reschedule.
        """
        reply = _make_reply()
        with (
            patch("apps.comments.models.Comment") as MockComment,
            patch(
                "apps.notifications.tasks.send_reply_notification",
                side_effect = Exception("SMTP down")
            ),
            patch.object(
                notify_reply_author,
                "retry",
                side_effect = Exception("retry called")
            ) as mock_retry
        ):
            MockComment.objects.select_related.return_value.get.return_value = reply

            with pytest.raises(Exception, match = "retry called"):
                notify_reply_author.run("reply-uuid")

        mock_retry.assert_called_once()
