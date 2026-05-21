import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.comments.models import Comment
from apps.notifications.tasks import notify_reply_author

log = logging.getLogger(__name__)

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
    # -----WS broadcast-----
    channel_layer = get_channel_layer()

    if channel_layer is None:
        log.warning(
            "No channel layer configured — WebSocket broadcast skipped."
        )
        return

    # prepare WS payload
    payload = {
        "type": "comment.broadcast",
        "id": str(comment.id),
        "text": comment.text,
        "created_at": comment.created_at.isoformat(),
        "username": comment.user.username,
        "email": comment.user.email,
        "home_page": comment.user.home_page,
        "parent_id": str(comment.parent_id) if comment.parent_id else None,
    }

    try:
        async_to_sync(channel_layer.group_send)(COMMENTS_GROUP, payload)
        log.debug(
            f"Broadcasted comment {comment.id} to group '{COMMENTS_GROUP}'"
        )
    except Exception as exc:
        log.error(f"WebSocket broadcast failed: {exc}", exc_info=True)

    # ----Celery notification task-----
    if comment.parent_id:
        try:
            notify_reply_author.delay(str(comment.id))
            log.debug(f"Queued reply notification for comment {comment.id}")
        except Exception as exc:
            log.error(
                f"Failed to queue notifcation for comment {comment.id}: {exc}",
                exc_info=True,
            )
