import logging
from dataclasses import dataclass

from django.core.mail import send_mail
from django.conf import settings


log = logging.getLogger(__name__)


@dataclass
class ReplyNotificationData:
    """Value object carrying all data needed to render the email."""
    recipient_email: str
    recipient_username: str
    reply_author: str
    parent_text: str
    reply_text: str
    comment_id: str


def send_reply_notification(data: ReplyNotificationData) -> None:
    """Send email notification to parent comment author.

    :param data: ReplyNotificationData value object.
    """
    subject = f"Someone replied to your comment"

    message = (
        f"Hi {data.recipient_username},\n\n"
        f"{data.reply_author} replied to your comment:\n\n"
        f"Your comment:\n  \"{data.parent_text[:100]}...\"\n\n"
        f"Their reply:\n  \"{data.reply_text}\"\n\n"
        f"Comment ID: {data.comment_id}\n"
    )

    try:
        send_mail(
            subject = subject,
            message = message,
            from_email = settings.DEFAULT_FROM_EMAIL,
            recipient_list = [data.recipient_email],
            fail_silently = False,
        )
        log.info(f"Reply notification sent to {data.recipient_email}")
    except Exception as exc:
        log.error(
            f"Failed to send reply message to {data.recipient_email}: {exc}",
            exc_info = True,
        )
        raise   # propagates back to the Celery task - Celery can retry
