import logging

from celery import shared_task

from apps.notifications.emails import (
    ReplyNotificationData,
    send_reply_notification,
)

log = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # retry after 60 seconds
    name="notifications.notify_reply_author",
)
def notify_reply_author(self, comment_id: str) -> None:
    """Async task: email the parent comment's author about a new reply.

    Uses `bind=True` making `self` (the task instance) available for retries.
    Fetches fresh data from DB - DB state is the source of truth.

    Retry strategy: up to 3 attempts, 60s apart.
    This handles transient SMTP failures gracefully.

    :param self: Celery task instance (for retries).
    :param comment_id: UUID string of the reply comment (not the parent).
    """
    log.info(f"notify_reply_author: processing comment_id={comment_id}")

    try:
        # avoid circular imports at module load time
        from apps.comments.models import Comment

        # fetch the reply with its parent and both users in one query
        reply = Comment.objects.select_related("user", "parent__user").get(
            id=comment_id
        )

        if not reply.parent:
            log.warning(
                f"Comment {comment_id} has no parent - skipping notification"
            )
            return

        parent = reply.parent

        # don't notify if the author is replying to themselves
        if parent.user_id == reply.user_id:
            log.debug(
                f"Self-reply by user {reply.user_id} - skipping notification"
            )
            return

        data = ReplyNotificationData(
            recipient_email=parent.user.email,
            recipient_username=parent.user.username,
            reply_author=reply.user.username,
            parent_text=parent.text,
            reply_text=reply.text,
            comment_id=str(reply.id),
        )

        send_reply_notification(data)

    except Exception as exc:
        log.error(f"notify_reply_author failed: {exc}", exc_info=True)
        # Celery retry - raise retry not return
        raise self.retry(exc=exc)
