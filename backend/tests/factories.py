import factory
from factory.django import DjangoModelFactory

from apps.comments.models import Comment
from apps.users.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    # declarations - generating model's field values
    # global counter that increments across the entire test session
    username = factory.Sequence(lambda n: f"user{n}")
    # evaluated after username is resolved
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    home_page = None
    # random valid IP
    ip_address = factory.Faker("ipv4")
    # realistic browser user-agent string
    user_agent = factory.Faker("user_agent")


class CommentFactory(DjangoModelFactory):
    # CommentFactory() call creates 2 DB rows: one User + one Comment.
    # The comment always has a valid, saved user
    class Meta:
        model = Comment

    user = factory.SubFactory(UserFactory)
    # multi-sentence English paragraph
    text = factory.Faker("paragraph")
    parent = None  # top-level by default

    class Params:
        # CommentFactory(as_reply=True) creates a parent first, then this reply.
        as_reply = factory.Trait(
            parent=factory.SubFactory("tests.factories.CommentFactory")
        )
