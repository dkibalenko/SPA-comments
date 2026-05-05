import re

from rest_framework import serializers

from apps.comments.models import Comment
from apps.users.serializers import UserIdentitySerializer, UserOutputSerializer
from apps.attachments.serializers import AttachmentSerializer


class CommentTreeSerializer(serializers.Serializer):
    """Read-only recursive serializer for the tree endpoint.

    Serializes the nested dict structure built by CommentService._build_tree().
    The plain Serializer working on dicts (from raw CTE), not a ModelSerializer
    working on ORM instances.
    Replies are serialized recursively — each reply is itself a full node.
    """
    id = serializers.UUIDField()
    parent_id = serializers.UUIDField(allow_null=True)
    text = serializers.CharField()
    created_at = serializers.DateTimeField()
    username = serializers.CharField()
    email = serializers.EmailField()
    home_page = serializers.URLField(allow_null=True)
    depth = serializers.IntegerField()
    replies = serializers.SerializerMethodField()

    # Attachment fields from CTE
    attachment_type     = serializers.CharField(allow_null=True)
    attachment_filename = serializers.CharField(allow_null=True)
    attachment_path     = serializers.CharField(allow_null=True)

    def get_replies(self, obj: dict) -> list:
        """Recursively serialize replies.

        SerializerMethodField allows calling the same serializer
        on each reply, enabling infinite nesting depth.
        """
        return CommentTreeSerializer(obj.get("replies", []), many=True).data


class CommentListSerializer(serializers.ModelSerializer):
    """Read-only flat representation for the paginated main list.

    Used by GET /api/comments/ — top-level comments only.
    Embeds user identity as a nested object.
    """
    user = UserOutputSerializer(read_only=True)
    reply_count = serializers.IntegerField(read_only=True)
    attachment = AttachmentSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "text",
            "created_at",
            "reply_count",
            "attachment"
        ]


class CommentCreateSerializer(serializers.Serializer):
    """Validates the full comment creation payload.

    Combines user identity fields + comment fields in one payload
    because the frontend submits everything together.
    `parent_id` is optional — `None` means top-level comment.
    """
    # User identity fields
    username = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    home_page = serializers.URLField(required=False, allow_null=True)

    # Comment fields
    text = serializers.CharField()
    parent_id = serializers.UUIDField(required=False, allow_null=True)

    # Captcha - required on every submission
    captcha_token = serializers.CharField()
    captcha_answer = serializers.CharField()

    def validate_username(self, value: str) -> str:
        if not re.match(r"^[a-zA-Z0-9]+$", value):
            raise serializers.ValidationError(
                "Username may only contain letters and digits [a-zA-Z0-9]."
            )
        return value

    def validate_text(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Comment text cannot be empty.")
        return value
