from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from apps.comments.handlers import on_comment_created, COMMENTS_GROUP


def _make_comment(parent_id: int = None) -> MagicMock:
    """Helper to create a mock Comment instance with realistic attributes.

    `parent_id` is optional to test both top-level and reply comments.
    """
    comment = MagicMock()
    comment.id = "comment-uuid"
    comment.text = "Hello world"
    comment.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # comment.user is a MagicMock with its own attributes
    comment.user.username = "alice"
    comment.user.email = "alice@example.com"
    comment.user.home_page = None
    comment.parent_id = parent_id
    return comment


def _call_handler(comment: MagicMock, mock_layer: MagicMock) -> None:
    """Invoke the signal handler with a mocked channel layer.

    `get_channel_layer` is replaced with a mock that returns `mock_layer` - a
    MagicMock passed in by each test. This means `channel_layer.group_send` is
    a MagicMock method that records its calls without touching Redis.

    `async_to_sync` is replaced by the identity function so
    channel_layer.group_send is called directly (no event loop needed).
    The identity patch makes it return `fn` unchanged, so the line becomes:
    `channel_layer.group_send(COMMENTS_GROUP, payload)` - a plain synchronous
    MagicMock call that records its arguments.
    """
    with (
        patch(
            "apps.comments.handlers.get_channel_layer",
            return_value = mock_layer
        ),
        patch(
            "apps.comments.handlers.async_to_sync",
            side_effect = lambda fn: fn
        )
    ):
        on_comment_created(sender = object, comment = comment)


class TestOnCommentCreated:

    def test_no_channel_layer_returns_without_error(self):
        """
        Test that if no channel layer is configured, the handler logs a warning
        and returns without raising an exception.
        """
        with patch("apps.comments.handlers.get_channel_layer", return_value = None):
            on_comment_created(sender = object, comment = _make_comment())  # must not raise

    def test_group_send_called_with_correct_group(self):
        """Test that the channel layer's group_send method is called with the correct group name."""
        mock_layer = MagicMock()
        _call_handler(_make_comment(), mock_layer)
        group_name = mock_layer.group_send.call_args[0][0]
        assert group_name == COMMENTS_GROUP

    def test_payload_contains_required_fields(self):
        """Test that the payload sent to group_send contains all required fields."""
        mock_layer = MagicMock()
        comment = _make_comment()
        _call_handler(comment, mock_layer)
        payload = mock_layer.group_send.call_args[0][1]
        for field in ("type", "id", "text", "created_at", "username", "email"):
            assert field in payload

    def test_payload_type_is_comment_broadcast(self):
        """Test that the payload's 'type' field is set to 'comment.broadcast'.

        The "type" key is the Channels dispatch mechanism - the consumer's method
        that handles this message is named by converting "comment.broadcast" → comment_broadcast.
        If this value is wrong, the consumer receives the message but no handler method is found and
        the message is silently dropped. Verifying the exact string is important.
        """
        mock_layer = MagicMock()
        _call_handler(_make_comment(), mock_layer)
        payload = mock_layer.group_send.call_args[0][1]
        assert payload["type"] == "comment.broadcast"

    def test_payload_parent_id_is_none_for_top_level(self):
        """
        Test that for a top-level comment (no parent), the payload's 'parent_id'
        field is None, not a string.
        """
        mock_layer = MagicMock()
        _call_handler(_make_comment(parent_id = None), mock_layer)
        payload = mock_layer.group_send.call_args[0][1]
        assert payload["parent_id"] is None

    def test_payload_parent_id_stringified_for_reply(self):
        """Test that for a reply comment (with parent), the payload's 'parent_id' field is a string."""
        mock_layer = MagicMock()
        _call_handler(_make_comment(parent_id = "parent-uuid"), mock_layer)
        payload = mock_layer.group_send.call_args[0][1]
        assert payload["parent_id"] == "parent-uuid"

    def test_group_send_exception_does_not_propagate(self):
        """
        Test that if the channel layer's group_send method raises an exception,
        it is caught and does not propagate.

        The handler wraps the broadcast in try/except Exception to prevent a Redis
        failure from breaking the HTTP response. The test verifies the exception is
        swallowed - just no exception reaching the test.
        """
        mock_layer = MagicMock()
        mock_layer.group_send.side_effect = Exception("Redis down")
        _call_handler(_make_comment(), mock_layer)  # must not raise

    def test_reply_queues_celery_task(self):
        """
        Test that if the comment is a reply (has a parent_id), the notify_reply_author
        Celery task is queued with the correct comment ID.
        The handler should call notify_reply_author.delay with the comment's ID as a string.
        """
        mock_layer = MagicMock()
        with patch("apps.comments.handlers.notify_reply_author") as mock_task:
            _call_handler(_make_comment(parent_id = "parent-uuid"), mock_layer)
        mock_task.delay.assert_called_once_with("comment-uuid")

    def test_top_level_comment_does_not_queue_celery_task(self):
        """
        Test that if the comment is a top-level comment (no parent_id), the notify_reply_author Celery task is not queued.
        The handler should not call notify_reply_author.delay for top-level comments.
        """
        mock_layer = MagicMock()
        with patch("apps.comments.handlers.notify_reply_author") as mock_task:
            _call_handler(_make_comment(parent_id = None), mock_layer)
        mock_task.delay.assert_not_called()

    def test_celery_task_exception_does_not_propagate(self):
        """
        Test that if the notify_reply_author Celery task raises an exception,
        it is caught and does not propagate.

        The signal handler must never let a Celery broker failure crash the HTTP response,
        same as the WebSocket broadcast guard.
        """
        mock_layer = MagicMock()
        with patch("apps.comments.handlers.notify_reply_author") as mock_task:
            mock_task.delay.side_effect = Exception("Celery down")
            _call_handler(_make_comment(parent_id = "parent-uuid"), mock_layer)  # must not raise
