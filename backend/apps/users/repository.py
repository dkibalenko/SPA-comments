from apps.users.models import User


class UserRepository:
    """Data access layer for User identity records."""

    def get_or_create_by_identity(
        self,
        username: str,
        email: str,
        ip_address: str,
        user_agent: str,
        home_page: str | None = None,
    ) -> tuple[User, bool]:
        """Fetch existing user by username+email or create a new one.

        username+email is the natural key — the same person reusing
        the same credentials gets the same User record.

        `ip_address` and user_agent are always updated to the latest
        values to track the most recent connection details.

        :returns: (`user_instance`, `created`)
        """
        user, created = User.objects.get_or_create(
            username=username,
            email=email,
            defaults={  # only used when create, not lookup
                "home_page": home_page,
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        )

        if not created:
            user.ip_address = ip_address
            user.user_agent = user_agent
            user.save(update_fields=["ip_address", "user_agent"])

        return user, created
