from rest_framework import serializers

from apps.users.models import User


class UserOutputSerializer(serializers.ModelSerializer):
    """Read-only representation of a user — embedded in comment responses."""

    class Meta:
        model = User
        fields = ["username", "email", "home_page"]
