import re

from rest_framework import serializers

from apps.users.models import User


USERNAME_RE = re.compile(r"^[a-zA-Z0-9]+$")


class UserIdentitySerializer(serializers.Serializer):
    """Validate the identity fields submitted with every comment."""

    username = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    home_page = serializers.URLField(required=False, allow_null=True)

    def validate_username(self, value: str) -> str:
        """Validate that username contains only letters and digits."""
        if not USERNAME_RE.match(value):
            raise serializers.ValidationError(
                "Username may only contain letters and digits [a-zA-Z0-9]."
            )
        return value


class UserOutputSerializer(serializers.ModelSerializer):
    """Read-only representation of a user — embedded in comment responses."""

    class Meta:
        model = User
        fields = ["username", "email", "home_page"]
