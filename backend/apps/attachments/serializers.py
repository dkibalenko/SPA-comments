from rest_framework import serializers
from apps.attachments.models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["file_type", "original_filename", "url"]

    def get_url(self, obj) -> str:
        """Return absolute URL if request in context, else relative URL.

        The context with request is passed by `CommentViewSet`'s `list` action
        to the root `CommentListSerializer` explicitly. Every nested serializer
        and every field at any depth automatically sees the same context.

        When `AttachmentSerializer.get_url` calls `self.context`, it:
        
        1. calls `self.root` — walks parent pointers up the chain until it
        finds the serializer with no parent
        2. that root is `CommentListSerializer`, the parent of
        `AttachmentSerializer`
        3. returns `CommentListSerializer._context` — which is
        `{"request": request}`

        The serializer itself has no idea what host it's running on.
        `request.build_absolute_uri()` is the only thing that knows the scheme
        (http vs https), the host, and the port at the time of
        the actual request. 
        """
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.storage_path.url)  # prepends MEDIA_URL
        return obj.storage_path.url
