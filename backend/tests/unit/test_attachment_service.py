from unittest.mock import MagicMock, patch

import pytest

from apps.attachments.models import AttachmentType
from apps.attachments.services import AttachmentService
from core.exceptions import UnsupportedFileTypeError, FileTooLargeError


def _make_file(content_type = "image/png", name = "photo.png"):
    f = MagicMock()
    f.content_type = content_type
    f.name = name
    return f


# AttachmentService.handle_upload

class TestHandleUpload:

    def _run(self, file, comment_id="comment-uuid"):
        with patch("apps.attachments.services.AttachmentStrategy.get_processor") as mock_get, \
             patch("apps.attachments.services.Attachment.objects.create") as mock_create:

            mock_processor = MagicMock()
            mock_processor.process.return_value = MagicMock()
            mock_get.return_value = mock_processor

            result = AttachmentService().handle_upload(comment_id=comment_id, file=file)
            return result, mock_get, mock_processor, mock_create

    def test_happy_path_returns_attachment(self):
        """Verifies that the service returns the Attachment instance created by the ORM."""
        file = _make_file()
        result, _, _, mock_create = self._run(file)
        assert result is mock_create.return_value  # return value is auto-created mock

    def test_processor_selected_via_strategy(self):
        """Verifies that the service calls AttachmentStrategy.get_processor() with the uploaded file."""
        file = _make_file()
        _, mock_get, _, _ = self._run(file)
        mock_get.assert_called_once_with(file)

    def test_validate_called_on_processor(self):
        """Verifies that the service calls validate() on the processor returned by the strategy."""
        file = _make_file()
        _, _, mock_processor, _ = self._run(file)
        mock_processor.validate.assert_called_once()

    def test_process_called_on_processor(self):
        """
        Verifies that the service calls process() on the processor, and that the processed file
        is what gets passed to the Attachment.objects.create() call as storage_path.
        """
        file = _make_file()
        _, _, mock_processor, _ = self._run(file)
        mock_processor.process.assert_called_once()

    def test_attachment_persisted_with_correct_fields(self):
        """
        Tests that Attachment.objects.create() is called with the right args based on
        the file and processor output.
        """
        file = _make_file(content_type = "image/jpeg", name = "photo.jpg")
        _, _, mock_processor, mock_create = self._run(file, comment_id = "cid-123")

        mock_create.assert_called_once_with(
            comment_id = "cid-123",
            file_type = AttachmentType.IMAGE,
            storage_path = mock_processor.process.return_value,
            original_filename = "photo.jpg",
        )

    def test_unsupported_file_type_propagates(self):
        """
        Simulate an unsupported file type by having the strategy's get_processor()
        raise UnsupportedFileTypeError.

        Verifies that the service lets it propagate - no swallowing.
        The view layer (`create()` in the ViewSet) catches it and returns a 400
        """
        file = _make_file(content_type = "application/exe")
        with patch(
            "apps.attachments.services.AttachmentStrategy.get_processor",
            side_effect = UnsupportedFileTypeError("not allowed"),
        ):
            with pytest.raises(UnsupportedFileTypeError):
                AttachmentService().handle_upload(comment_id = "cid", file = file)

    def test_file_too_large_propagates(self):
        """
        Simulate a file that's too large by having the processor's validate()
        raise FileTooLargeError.

        Verifies that FileTooLargeError error propagates up untouched.
        """
        file = _make_file()
        with patch("apps.attachments.services.AttachmentStrategy.get_processor") as mock_get:
            mock_processor = MagicMock()
            mock_processor.validate.side_effect = FileTooLargeError("too big")
            mock_get.return_value = mock_processor

            with pytest.raises(FileTooLargeError):
                AttachmentService().handle_upload(comment_id = "cid", file = file)


# AttachmentService._resolve_type

class TestResolveType:

    def test_image_mime_returns_image_type(self):
        assert AttachmentService._resolve_type("image/png") == AttachmentType.IMAGE

    def test_image_jpeg_returns_image_type(self):
        assert AttachmentService._resolve_type("image/jpeg") == AttachmentType.IMAGE

    def test_text_mime_returns_text_type(self):
        assert AttachmentService._resolve_type("text/plain") == AttachmentType.TEXT

    def test_unknown_mime_returns_text_type(self):
        assert AttachmentService._resolve_type("application/pdf") == AttachmentType.TEXT
