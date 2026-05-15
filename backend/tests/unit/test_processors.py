from io import BytesIO

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

from apps.attachments.processors import (
    IMAGE_MAX_HEIGHT,
    IMAGE_MAX_SIZE_BYTES,
    IMAGE_MAX_WIDTH,
    TEXT_MAX_SIZE_BYTES,
    ImageProcessor,
    TextFileProcessor,
)
from core.exceptions import FileTooLargeError, UnsupportedFileTypeError


# helpers

def make_image_file(
    width: int,
    height: int,
    fmt: str = "PNG",
    content_type: str = "image/png",
    name: str = "test.png",
) -> InMemoryUploadedFile:
    """Creates an in-memory image file of the specified dimensions and format.

    The image content is just a blank canvas.
    The file is returned as an InMemoryUploadedFile, suitable for testing the processors.
    """
    buf = BytesIO()
    mode = "P" if fmt == "GIF" else "RGB"
    Image.new(mode, (width, height)).save(buf, format = fmt)
    buf.seek(0)
    return InMemoryUploadedFile(
        file = buf,
        field_name = "attachment",
        name = name,
        content_type = content_type,
        size = buf.getbuffer().nbytes,
        charset = None,
    )


def make_text_file(
    content: bytes = b"hello",
    name: str = "note.txt",
    content_type: str = "text/plain",
) -> InMemoryUploadedFile:
    """Creates an in-memory text file with the specified content."""
    buf = BytesIO(content)
    return InMemoryUploadedFile(
        file = buf,
        field_name = "attachment",
        name = name,
        content_type = content_type,
        size = len(content),
        charset = None,
    )


# ImageProcessor.validate

class TestImageProcessorValidate:

    @pytest.mark.parametrize(
        "name, content_type, fmt",
        [
            ("photo.jpg", "image/jpeg", "JPEG"),
            ("photo.jpeg", "image/jpeg", "JPEG"),
            ("photo.png", "image/png", "PNG"),
            ("photo.gif", "image/gif", "GIF"),
        ],
    )
    def test_allowed_types_pass(self, name, content_type, fmt):
        """Test that valid image types and matching extensions pass validation."""
        f = make_image_file(100, 100, fmt = fmt, content_type = content_type, name = name)
        ImageProcessor(f).validate()  # must not raise

    def test_unsupported_content_type_raises(self):
        """Test that a MIME type not in ALLOWED_IMAGE_TYPES raises an error."""
        f = make_image_file(100, 100, name = "photo.bmp", content_type = "image/bmp")
        with pytest.raises(UnsupportedFileTypeError):
            ImageProcessor(f).validate()

    def test_mismatched_extension_raises(self):
        """Test that a valid MIME type but extension not in ALLOWED_IMAGE_EXTENSIONS raises an error."""
        f = make_image_file(100, 100, content_type = "image/png", name = "photo.bmp")
        with pytest.raises(UnsupportedFileTypeError):
            ImageProcessor(f).validate()

    def test_file_exceeding_size_limit_raises(self):
        """Test that a file exceeding the size limit raises an error."""
        f = make_image_file(100, 100, name = "big.png")
        f.size = IMAGE_MAX_SIZE_BYTES + 1
        with pytest.raises(FileTooLargeError):
            ImageProcessor(f).validate()

    def test_file_at_size_limit_passes(self):
        """Test that a file exactly at the size limit passes validation."""
        f = make_image_file(100, 100, name = "ok.png")
        f.size = IMAGE_MAX_SIZE_BYTES
        ImageProcessor(f).validate()  # at limit must pass


# ImageProcessor.process

class TestImageProcessorProcess:

    def test_image_within_bounds_returned_as_is(self):
        """Test that an image within the maximum dimensions is returned as-is."""
        f = make_image_file(IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT)
        result = ImageProcessor(f).process()
        assert result is f

    def test_small_image_returned_as_is(self):
        """Test that a small image is returned as-is without modification."""
        f = make_image_file(100, 80)
        result = ImageProcessor(f).process()
        assert result is f

    def test_wide_image_resized_within_max_dimensions(self):
        """Test that a wide image is resized to fit within max dimensions."""
        f = make_image_file(640, 100)
        result = ImageProcessor(f).process()
        img = Image.open(result)
        assert img.width <= IMAGE_MAX_WIDTH
        assert img.height <= IMAGE_MAX_HEIGHT

    def test_tall_image_resized_within_max_dimensions(self):
        """Test that a tall image is resized to fit within max dimensions."""
        f = make_image_file(100, 480)
        result = ImageProcessor(f).process()
        img = Image.open(result)
        assert img.width <= IMAGE_MAX_WIDTH
        assert img.height <= IMAGE_MAX_HEIGHT

    def test_oversized_image_preserves_aspect_ratio(self):
        """Test that an oversized image is resized proportionally, preserving aspect ratio."""
        # 640×480 — 4:3 ratio; thumbnail must preserve it
        f = make_image_file(640, 480)
        result = ImageProcessor(f).process()
        img = Image.open(result)
        # compute new aspect ratio, compare to original ratio (4/3), allow a tiny tolerance of 0.02
        assert abs(img.width / img.height - 4 / 3) < 0.02

    def test_gif_converted_to_png_on_resize(self):
        """Test that a GIF image is converted to PNG format when resized."""
        f = make_image_file(640, 480, fmt = "GIF", content_type = "image/gif", name = "anim.gif")
        result = ImageProcessor(f).process()
        assert result.content_type == "image/png"
        assert result.name.endswith(".png")

    def test_jpeg_keeps_original_content_type_on_resize(self):
        """Test that a JPEG image keeps its content type after resizing."""
        f = make_image_file(640, 480, fmt = "JPEG", content_type = "image/jpeg", name = "photo.jpg")
        result = ImageProcessor(f).process()
        assert result.content_type == "image/jpeg"

    def test_resized_result_is_readable_image(self):
        """Test that the output of processing an oversized image is a valid image file."""
        f = make_image_file(1000, 800)
        result = ImageProcessor(f).process()
        img = Image.open(result)
        assert img.width > 0 and img.height > 0


# TextFileProcessor.validate

class TestTextFileProcessorValidate:

    def test_valid_txt_passes(self):
        """Test that a valid text file with correct MIME type and extension passes validation."""
        f = make_text_file(b"some text", name = "note.txt", content_type = "text/plain")
        TextFileProcessor(f).validate()  # must not raise

    def test_unsupported_content_type_raises(self):
        """Test that a MIME type not in ALLOWED_TEXT_TYPES raises an error."""
        f = make_text_file(b"data", name = "data.csv", content_type = "text/csv")
        with pytest.raises(UnsupportedFileTypeError):
            TextFileProcessor(f).validate()

    def test_wrong_extension_raises(self):
        """Test that a valid MIME type but extension not in ALLOWED_TEXT_EXTENSIONS raises an error."""
        f = make_text_file(b"data", name = "file.log", content_type = "text/plain")
        with pytest.raises(UnsupportedFileTypeError):
            TextFileProcessor(f).validate()

    def test_file_at_size_limit_passes(self):
        """Test that a text file exactly at the size limit passes validation."""
        f = make_text_file(b"x" * TEXT_MAX_SIZE_BYTES, name = "big.txt")
        TextFileProcessor(f).validate()  # exactly at limit — must pass

    def test_file_exceeding_size_limit_raises(self):
        """Test that a text file exceeding the size limit raises an error."""
        f = make_text_file(b"x", name = "big.txt")
        f.size = TEXT_MAX_SIZE_BYTES + 1
        with pytest.raises(FileTooLargeError):
            TextFileProcessor(f).validate()

    def test_process_returns_original_file(self):
        """Test that processing a text file returns the original file unchanged."""
        f = make_text_file(b"content")
        result = TextFileProcessor(f).process()
        assert result is f
