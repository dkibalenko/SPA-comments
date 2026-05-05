from rest_framework import serializers
from apps.attachments.models import Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["file_type", "original_filename", "url"]

    def get_url(self, obj) -> str:
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.storage_path.url)
        return obj.storage_path.url
