import pytest

from apps.users.models import User
from apps.users.repository import UserRepository
from tests.factories import UserFactory


def _call(repo: UserRepository, **overrides):
    """Helper to call get_or_create_by_identity with default values, overridden by test."""
    kwargs = dict(
        username = "alice",
        email = "alice@example.com",
        ip_address = "1.2.3.4",
        user_agent = "TestBrowser/1.0",
    )
    kwargs.update(overrides)
    return repo.get_or_create_by_identity(**kwargs)


@pytest.mark.django_db
class TestGetOrCreateByIdentity:

    def test_new_user_is_created(self):
        _, created = _call(UserRepository())
        assert created is True

    def test_new_user_row_inserted(self):
        _call(UserRepository())
        assert User.objects.count() == 1

    def test_returns_user_with_correct_identity(self):
        user, _ = _call(UserRepository())
        assert user.username == "alice"
        assert user.email == "alice@example.com"

    def test_existing_user_returned_on_same_identity(self):
        UserFactory(username="alice", email="alice@example.com")  # inserts a row directly
        _, created = _call(UserRepository())  # goes via repo
        assert created is False  # lookup hits existing row

    def test_existing_user_no_duplicate_row(self):
        UserFactory(username = "alice", email = "alice@example.com")
        _call(UserRepository())
        assert User.objects.count() == 1

    def test_existing_user_ip_updated(self):
        UserFactory(username = "alice", email = "alice@example.com", ip_address="1.1.1.1")
        user, _ = _call(UserRepository(), ip_address = "9.9.9.9")
        assert user.ip_address == "9.9.9.9"
        # verify persisted to DB, not just the in-memory object
        assert User.objects.get(username="alice").ip_address == "9.9.9.9"

    def test_existing_user_agent_updated(self):
        UserFactory(username = "alice", email = "alice@example.com")
        user, _ = _call(UserRepository(), user_agent="NewBrowser/2.0")
        assert user.user_agent == "NewBrowser/2.0"
        assert User.objects.get(username="alice").user_agent == "NewBrowser/2.0"

    def test_same_username_different_email_creates_separate_user(self):
        repo = UserRepository()
        _call(repo, email="a@example.com")
        _call(repo, email="b@example.com")
        assert User.objects.count() == 2

    def test_home_page_stored_on_create(self):
        user, _ = _call(UserRepository(), home_page = "https://alice.example.com")
        assert user.home_page == "https://alice.example.com"

    def test_home_page_not_overwritten_on_return(self):
        """home_page is only set at creation; returning users keep their original value."""
        UserFactory(
            username="alice",
            email="alice@example.com",
            home_page="https://original.example.com",
        )
        user, _ = _call(UserRepository(), home_page = "https://new.example.com")
        assert user.home_page == "https://original.example.com"
