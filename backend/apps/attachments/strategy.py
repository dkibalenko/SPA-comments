from django.core.files.uploadedfile import InMemoryUploadedFile

from apps.attachments.interfaces import AttachmentProcessorInterface
from apps.attachments.processors import (
    ImageProcessor,
    TextFileProcessor,
)
from core.exceptions import UnsupportedFileTypeError


class AttachmentStrategy:
    """Returns the correct processor for a given file."""

    _registry: dict[str, type[AttachmentProcessorInterface]] = {
        "image/jpeg": ImageProcessor,
        "image/png": ImageProcessor,
        "image/gif": ImageProcessor,
        "text/plain": TextFileProcessor,
    }

    @classmethod
    def get_processor(
        cls,
        file: InMemoryUploadedFile
    ) -> AttachmentProcessorInterface:
        """Resolve processor by MIME content type.

        :param file: The uploaded file from request.FILES.
        :returns: An instance of the appropriate processor class.
        :raises UnsupportedFileTypeError: If content_type not registered.
        """
        processor_class = cls._registry.get(file.content_type)
        if not processor_class:
            raise UnsupportedFileTypeError(
                f"File type '{file.content_type}' is not supported. "
                f"Allowed: JPG, PNG, GIF images and TXT files."
            )
        return processor_class(file)
