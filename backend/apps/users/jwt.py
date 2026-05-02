from datetime import timedelta

from rest_framework_simplejwt.tokens import Token

from apps.users.models import User


class CommentIdentityToken(Token):
    """Anonymous identity token issued after comment creation.

    Encodes username + email. The frontend can pre-fill
    the comment form on the next submission.

    Not an authentication token — it grants no permissions.
    It's a signed identity hint, nothing more.
    """
    token_type = "comment_identity"
    lifetime = timedelta(days=30)


def issue_identity_token(user: User) -> str:
    """Issue a signed JWT for a commenter identity.

    :param user: apps.users.models.User instance.
    :returns: Encoded JWT string.
    """
    token = CommentIdentityToken()
    token["user_id"] = str(user.id)
    token["username"] = user.username
    token["email"] = user.email
    return str(token)
