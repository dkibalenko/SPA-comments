import django_filters

from apps.comments.models import Comment


class CommentFilter(django_filters.FilterSet):
    """Enables sorting top-level comments by username, email, date."""
    ordering = django_filters.OrderingFilter(
        fields=(
            # (model field, query param name)
            ("username_lower", "username"),  # use annotation field
            ("user__email", "email"),
            ("created_at", "date"),
        ),
        field_labels={
            "username": "User Name",
            "email": "E-mail",
            "date": "Date Added",
        },
    )

    class Meta:
        model = Comment
        fields = []
