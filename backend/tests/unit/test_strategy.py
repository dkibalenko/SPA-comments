import pytest
from unittest.mock import MagicMock

from apps.attachments.processors import ImageProcessor, TextFileProcessor
from apps.attachments.strategy import AttachmentStrategy
from core.exceptions import UnsupportedFileTypeError


def make_mock_file(content_type: str) -> MagicMock:
    f = MagicMock()
    f.content_type = content_type
    return f


class TestAttachmentStrategyGetProcessor:

    @pytest.mark.parametrize(
        "content_type, expected_class",
        [
            ("image/jpeg", ImageProcessor),
            ("image/png", ImageProcessor),
            ("image/gif", ImageProcessor),
            ("text/plain", TextFileProcessor),
        ],
    )
    def test_returns_correct_processor_for_mime_type(self, content_type, expected_class):
        """Test that the strategy returns the correct processor instance based on MIME type."""
        f = make_mock_file(content_type)
        processor = AttachmentStrategy.get_processor(f)
        assert isinstance(processor, expected_class)

    def test_processor_holds_reference_to_file(self):
        """Test that the returned processor instance has a reference to the original file."""
        f = make_mock_file("image/png")
        processor = AttachmentStrategy.get_processor(f)
        assert processor.file is f

    def test_unknown_content_type_raises(self):
        """Test that an unsupported MIME type raises the correct exception."""
        f = make_mock_file("application/pdf")
        with pytest.raises(UnsupportedFileTypeError):
            AttachmentStrategy.get_processor(f)

    def test_empty_content_type_raises(self):
        """Test that an empty MIME type raises the correct exception."""
        f = make_mock_file("")
        with pytest.raises(UnsupportedFileTypeError):
            AttachmentStrategy.get_processor(f)
