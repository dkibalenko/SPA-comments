import uuid

from django.db import models


class User(models.Model):
    """Represents the identity of a commenter.

    Not an auth user - no password, no login.
    Identity is established by username + email.
    A single person reusing the same username/email gets the
    same record.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        max_length=50, help_text="Letters and digits only [a-zA-z0-9]"
    )
    email = models.EmailField()
    home_page = models.URLField(blank=True, null=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["username", "email"], name="unique_user_identity"
            )
        ]
        indexes = [
            models.Index(fields=["email"], name="idx_users_email"),
            models.Index(fields=["username"], name="idx_users_username"),
        ]

    def __str__(self) -> str:
        return f"{self.username} <{self.email}>"
