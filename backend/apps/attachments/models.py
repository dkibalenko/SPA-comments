import uuid

from django.db import models


class AttachmentType(models.TextChoices):
    IMAGE = "image", "Image"
    TEXT = "text", "Text File"


class Attachment(models.Model):
    """One optional file per comment.

    Images are resized to max 320x240 before storate.
    Text files are capped at 100KB
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    comment = models.OneToOneField(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="attachment"
    )
    file_type = models.CharField(
        max_length=10,
        choices=AttachmentType.choices
    )
    storage_path = models.FileField(
        upload_to="attachments/%Y/%m"
    )
    original_filename = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.file_type} - {self.original_filename}"
