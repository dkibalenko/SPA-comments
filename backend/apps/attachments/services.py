from django.core.files.uploadedfile import InMemoryUploadedFile

from apps.attachments.models import Attachment, AttachmentType
from apps.attachments.strategy import AttachmentStrategy


class AttachmentService:
    """Orchestrates the full attachment pipeline.

    validate → process → save
    Each step is a separate concern handled by the right class.
    """

    def handle_upload(
        self,
        comment_id: str,
        file: InMemoryUploadedFile,
    ) -> Attachment:
        """Full pipeline: validate, process, persist.

        :param comment_id: UUID of the comment this file belongs to.
        :param file: The uploaded file from request.FILES.
        :returns: Saved Attachment instance.
        :raises UnsupportedFileTypeError: Wrong format.
        :raises FileTooLargeError: File too large.
        """
        processor = AttachmentStrategy.get_processor(file)

        processor.validate()

        processed_file = processor.process()

        file_type = self._resolve_type(file.content_type)

        attachment = Attachment.objects.create(
            comment_id=comment_id,
            file_type=file_type,
            storage_path=processed_file,
            original_filename=file.name,
        )

        return attachment

    @staticmethod
    def _resolve_type(content_type: str) -> tuple[str, str]:
        """Determine attachment type based on MIME content type."""
        if content_type.startswith("image/"):
            return AttachmentType.IMAGE
        return AttachmentType.TEXT
