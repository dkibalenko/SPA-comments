import os
from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

from apps.attachments.interfaces import AttachmentProcessorInterface
from core.exceptions import FileTooLargeError, UnsupportedFileTypeError

IMAGE_MAX_WIDTH = 320
IMAGE_MAX_HEIGHT = 240
IMAGE_MAX_SIZE_BYTES = 5 * 1024 * 1024   # 5MB pre-resize limit
TEXT_MAX_SIZE_BYTES = 100 * 1024         # 100KB

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
ALLOWED_TEXT_TYPES = {"text/plain"}
ALLOWED_TEXT_EXTENSIONS = {".txt"}


class ImageProcessor(AttachmentProcessorInterface):
    """Handles JPG, PNG, GIF uploads.

    Validates format and size, then proportionally resizes
    to fit within IMAGE_MAX_WIDTH x IMAGE_MAX_HEIGHT if larger.
    """

    def validate(self) -> None:
        """Check MIME type, extension, and size limits for images.

        Raises UnsupportedFileTypeError if MIME type or extension is unallowed.
        Raises FileTooLargeError if file size exceeds IMAGE_MAX_SIZE_BYTES.
        """
        ext = self._extension()
        if (
            self.file.content_type not in ALLOWED_IMAGE_TYPES
            or ext not in ALLOWED_IMAGE_EXTENSIONS
        ):
            raise UnsupportedFileTypeError(
                f"Unsupported image format '{ext}'. "
                f"Allowed: JPG, PNG, GIF."
            )
        if self.file.size > IMAGE_MAX_SIZE_BYTES:
            raise FileTooLargeError(
                f"Image exceeds maximum pre-resize size of "
                f"{IMAGE_MAX_SIZE_BYTES // (1024*1024)}MB."
            )

    def process(self) -> InMemoryUploadedFile:
        """Resize image proportionally if it exceeds max dimensions.

        Uses Pillow (PIL). GIFs are converted to PNG on resize
        to avoid complex frame handling.
        Returns the original file unchanged if within bounds.
        """
        image = Image.open(self.file)
        original_format = image.format or "PNG"

        if image.width <= IMAGE_MAX_WIDTH and image.height <= IMAGE_MAX_HEIGHT:
            # already within bounds — return as-is
            self.file.seek(0)
            return self.file

        # resize proportionally, never upscale
        image.thumbnail(
            (IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT), Image.Resampling.LANCZOS
        )

        # save resized image to in-memory buffer
        output = BytesIO()
        save_format = "PNG" if original_format == "GIF" else original_format
        image.save(output, format=save_format)
        output.seek(0)  # move pointer to start of buffer

        # for GIFs, convert to PNG. for others, keep original content type.
        content_type = (
            "image/png" if save_format == "PNG" else self.file.content_type
        )
        # swap extension if format changed, otherwise keep original name
        new_name = self._swap_extension(save_format)

        # create new InMemoryUploadedFile with resized content
        return InMemoryUploadedFile(
            file=output,
            field_name=self.file.field_name,
            name=new_name,
            content_type=content_type,
            size=output.getbuffer().nbytes,
            charset=None,
        )

    def _extension(self) -> str:
        """Extract file extension in lowercase (e.g. '.jpg')."""
        return os.path.splitext(self.file.name)[1].lower()

    def _swap_extension(self, fmt: str) -> str:
        """Change file extension based on format (e.g. GIF → PNG).

        Keeps original base name, just swaps extension.
        """
        base = os.path.splitext(self.file.name)[0]
        ext_map = {"PNG": ".png", "JPEG": ".jpg", "GIF": ".gif"}
        return base + ext_map.get(fmt, ".png")


class TextFileProcessor(AttachmentProcessorInterface):
    """Handles TXT uploads.

    Validates extension, content type, and 100KB size cap.
    No transformation — text files are stored as-is.
    """

    def validate(self) -> None:
        ext = os.path.splitext(self.file.name)[1].lower()
        if (
            self.file.content_type not in ALLOWED_TEXT_TYPES
            or ext not in ALLOWED_TEXT_EXTENSIONS
        ):
            raise UnsupportedFileTypeError(
                f"Unsupported file format '{ext}'. Only TXT allowed."
            )
        if self.file.size > TEXT_MAX_SIZE_BYTES:
            raise FileTooLargeError(
                f"Text file exceeds 100KB limit "
                f"({self.file.size // 1024}KB uploaded)."
            )

    def process(self) -> InMemoryUploadedFile:
        """No transformation needed — return as-is."""
        self.file.seek(0)
        return self.file
