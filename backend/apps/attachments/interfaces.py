import abc

from django.core.files.uploadedfile import InMemoryUploadedFile


class AttachmentProcessorInterface(abc.ABC):
    """Abstract base for all file processors."""

    def __init__(self, file: InMemoryUploadedFile) -> None:
        self.file = file

    @abc.abstractmethod
    def validate(self) -> None:
        """Validate the file. Raise on failure.

        :raises UnsupportedFileTypeError: Wrong format.
        :raises FileTooLargeError: Exceeds size limit.
        """

    @abc.abstractmethod
    def process(self) -> InMemoryUploadedFile:
        """Transform the file if needed and return ready-to-save version."""
