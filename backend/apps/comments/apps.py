from django.apps import AppConfig


class CommentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.comments"

    def ready(self) -> None:
        """Connect signal handlers when the app is fully loaded."""
        # import here to avoid AppRegistryNotReady - errors that occur when
        # signals are imported before models are loaded
        from apps.comments.signals import comment_created
        from apps.comments.handlers import on_comment_created

        comment_created.connect(
            on_comment_created,
            dispatch_uid="on_comment_created",  # prevents duplicate connections
        )
