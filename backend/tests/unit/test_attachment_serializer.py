from unittest.mock import MagicMock

from apps.attachments.serializers import AttachmentSerializer


class TestAttachmentSerializerGetUrl:

    def _make_obj(self, url="/media/attachments/2024/01/file.png"):
        """Helper to create a mock object with a storage_path.url attribute."""
        obj = MagicMock()
        obj.storage_path.url = url
        return obj

    def test_with_request_returns_absolute_uri(self):
        """Test that get_url returns the absolute URI when a request is provided in the context."""
        obj = self._make_obj()
        request = MagicMock()
        request.build_absolute_uri.return_value = "http://testserver/media/attachments/2024/01/file.png"

        serializer = AttachmentSerializer(obj, context={"request": request})
        url = serializer.get_url(obj)

        request.build_absolute_uri.assert_called_once_with(obj.storage_path.url)
        assert url == "http://testserver/media/attachments/2024/01/file.png"

    def test_without_request_returns_relative_url(self):
        """Test that get_url returns the relative URL when no request is provided in the context."""
        obj = self._make_obj(url="/media/attachments/2024/01/file.png")

        serializer = AttachmentSerializer(obj, context={})
        url = serializer.get_url(obj)

        assert url == "/media/attachments/2024/01/file.png"

    def test_missing_context_returns_relative_url(self):
        """Test that get_url returns the relative URL when context is not provided."""
        obj = self._make_obj(url="/media/file.txt")

        # context defaults to {} when not passed
        serializer = AttachmentSerializer(obj)
        url = serializer.get_url(obj)

        assert url == "/media/file.txt"
