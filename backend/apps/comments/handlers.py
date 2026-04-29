import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.comments.models import Comment

log = logging.getLogger(__name__)

# All clients subscribe to this single group.
# Every new comment broadcasts to everyone connected.
COMMENTS_GROUP = "comments"


def on_comment_created(sender, comment: Comment, **kwargs) -> None:
    """Signal handler: broadcast new comment to all WebSocket clients.

    Called synchronously (Django signals are sync) but Channels'
    group_send is async. async_to_sync() bridges this correctly —
    it runs the coroutine in the existing event loop if one exists,
    or creates a new one.

    :param sender: The class that fired the signal (CommentService).
    :param comment: The freshly persisted Comment instance.
    """
    # should send high-level events over the channel layer
    channel_layer = get_channel_layer()

    if channel_layer is None:
        log.warning(
            "No channel layer configured — WebSocket broadcast skipped."
        )
        return

    # prepare WS payload
    payload = {
        "type": "comment.broadcast",   # maps to consumer method name
        "id": str(comment.id),
        "text": comment.text,
        "created_at": comment.created_at.isoformat(),
        "username": comment.user.username,
        "email": comment.user.email,
        "home_page": comment.user.home_page,
        "parent_id": str(comment.parent_id) if comment.parent_id else None,
    }

    try:
        # channel layer broadcasts to group
        # Redis queues message for all connected WS consumers in that group
        async_to_sync(channel_layer.group_send)(COMMENTS_GROUP, payload)
        log.debug(
            f"Broadcasted comment {comment.id} to group '{COMMENTS_GROUP}'"
        )
    except Exception as exc:
        # Never let WS broadcast failure break the HTTP response
        log.error(f"WebSocket broadcast failed: {exc}", exc_info=True)
