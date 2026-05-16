import uuid

from django.db import models


class Comment(models.Model):
    """Supports infinite nesting via self-referential FK.

    `parent=None` means top-level comment.
    `parent=<Comment>` means reply.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(  # user_id is created for FK
        "users.User", on_delete=models.CASCADE, related_name="comments"
    )
    parent = models.ForeignKey(  # parent_id is created for FK
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    text = models.TextField(
        help_text="Sanitized. Allowed tags: <a>, <code>, <i>, <strong>"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["parent"], name="idx_comments_parent"),
            models.Index(
                fields=["-created_at"], name="idx_comments_created_desc"
            ),
        ]
        ordering = ["-created_at"]  # default LIFO

    def __str__(self) -> str:
        prefix = "Reply" if self.parent_id else "Comment"
        return f"{prefix} by {self.user_id} at {self.created_at}"
