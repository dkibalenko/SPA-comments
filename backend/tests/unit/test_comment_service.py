import pytest
from unittest.mock import MagicMock, patch

from apps.comments.services import CommentService
from core.exceptions import NotFoundError, ValidationError


# helpers

def _valid_kwargs() -> dict:
    return dict(
        username="alice",
        email="alice@example.com",
        text="<strong>Hello</strong>",
        ip_address="1.2.3.4",
        user_agent="Mozilla/5.0",
        captcha_token="token",
        captcha_answer="answer",
    )


def _mock_comment(parent_id = None) -> MagicMock:
    c = MagicMock()
    c.parent_id = parent_id
    return c


# CommentService.create_comment

class TestCreateComment:

    @pytest.fixture
    def service(self):
        return CommentService(
            comment_repo=MagicMock(),
            user_repo=MagicMock(),
            captcha_service=MagicMock(),
        )

    def test_happy_path_returns_comment_and_token(self, service):
        """Test the normal flow where everything succeeds and a comment is created."""
        mock_comment = _mock_comment()
        service.comment_repo.create.return_value = mock_comment
        service.comment_repo.get_by_id.return_value = mock_comment
        service.user_repo.get_or_create_by_identity.return_value = (MagicMock(), True)

        with (
            patch("apps.comments.services.issue_identity_token", return_value="jwt-tok"),
            patch("django.db.transaction.on_commit")
        ):
            result = service.create_comment(**_valid_kwargs())

        assert result["comment"] is mock_comment
        assert result["token"] == "jwt-tok"

    def test_captcha_failure_propagates(self, service):
        """If CAPTCHA validation fails, the error should propagate and no comment should be created."""
        service.captcha_service.validate.side_effect = ValidationError("bad captcha")
        with pytest.raises(ValidationError, match = "bad captcha"):
            service.create_comment(**_valid_kwargs())

    def test_whitespace_only_text_raises(self, service):
        """If the comment text is only whitespace, it should be considered empty and raise a ValidationError."""
        kwargs = {**_valid_kwargs(), "text": "   "}
        with pytest.raises(ValidationError, match = "empty"):
            service.create_comment(**kwargs)

    def test_nonexistent_parent_id_raises(self, service):
        """If the parent comment does not exist, a ValidationError should be raised."""
        service.comment_repo.get_by_id.return_value = None
        kwargs = {**_valid_kwargs(), "parent_id": "missing-uuid"}
        with pytest.raises(ValidationError, match="does not exist"):
            service.create_comment(**kwargs)

    def test_top_level_comment_invalidates_list_cache(self, service):
        """When creating a new top-level comment (no parent_id), the list cache should be invalidated."""
        mock_comment = _mock_comment()
        service.comment_repo.create.return_value = mock_comment
        service.comment_repo.get_by_id.return_value = mock_comment
        service.user_repo.get_or_create_by_identity.return_value = (MagicMock(), True)

        with (
            patch("apps.comments.services.issue_identity_token", return_value="tok"),
            patch("django.db.transaction.on_commit"),
            patch("apps.comments.services.invalidate_list_cache") as mock_inv
        ):
            service.create_comment(**_valid_kwargs())

        mock_inv.assert_called_once()

    def test_reply_invalidates_tree_cache(self, service):
        """When creating a reply (with a parent_id), the tree cache should be invalidated."""
        # parent has no parent_id → it is the root
        mock_parent = _mock_comment(parent_id = None)
        mock_comment = _mock_comment()
        service.comment_repo.create.return_value = mock_comment
        # get_by_id is called: (1) to validate parent existence,
        # (2) to reload after create, (3) inside _find_root_id
        # mock .side_effect = [] returns items in order on each successive call
        service.comment_repo.get_by_id.side_effect = [mock_parent, mock_comment, mock_parent]
        service.user_repo.get_or_create_by_identity.return_value = (MagicMock(), True)

        kwargs = {**_valid_kwargs(), "parent_id": "parent-uuid"}

        with (
            patch("apps.comments.services.issue_identity_token", return_value="tok"),
            patch("django.db.transaction.on_commit"),
            patch("apps.comments.services.invalidate_tree_cache") as mock_inv
        ):
            service.create_comment(**kwargs)

        mock_inv.assert_called_once()


# CommentService._find_root_id

class TestFindRootId:

    @pytest.fixture
    def service(self):
        return CommentService(comment_repo = MagicMock())

    def test_root_comment_returns_itself(self, service):
        """If the comment is a top-level (root) comment, _find_root_id should return its own ID."""
        service.comment_repo.get_by_id.return_value = _mock_comment(parent_id=None)
        assert service._find_root_id("root-id") == "root-id"

    def test_one_level_up(self, service):
        """If the comment is a reply to a root comment, _find_root_id should return the root comment's ID."""
        child = _mock_comment(parent_id = "root-id")
        root  = _mock_comment(parent_id = None)
        service.comment_repo.get_by_id.side_effect = [child, root]
        assert service._find_root_id("child-id") == "root-id"

    def test_two_levels_up(self, service):
        """If the comment is a reply to a reply, _find_root_id should still return the root comment's ID."""
        grandchild = _mock_comment(parent_id = "child-id")
        child      = _mock_comment(parent_id = "root-id")
        root       = _mock_comment(parent_id = None)
        service.comment_repo.get_by_id.side_effect = [grandchild, child, root]
        assert service._find_root_id("gc-id") == "root-id"

    def test_broken_chain_returns_current_id(self, service):
        """If get_by_id returns None (dangling pointer), return the last known id."""
        service.comment_repo.get_by_id.return_value = None
        assert service._find_root_id("orphan-id") == "orphan-id"

    def test_cycle_detected_returns_current_id(self, service):
        """If a cycle is detected in the parent chain, return the current id to prevent infinite loop."""
        # chain: a → b → a (cycle)
        a = _mock_comment(parent_id = "b-id")
        b = _mock_comment(parent_id = "a-id")
        service.comment_repo.get_by_id.side_effect = [a, b]
        # after visiting a then b, current_id becomes "a-id" again → cycle detected
        assert service._find_root_id("a-id") == "a-id"


# CommentService.get_tree

class TestGetTree:

    @pytest.fixture
    def service(self):
        return CommentService(comment_repo = MagicMock())

    def test_cache_hit_returns_cached_data_without_hitting_repo(self, service):
        """If Redis has the tree, return it immediately - no DB call."""
        cached_tree = [{"id": "root-id", "replies": []}]

        with patch("django.core.cache.cache.get", return_value = cached_tree):
            result = service.get_tree("root-id")

        assert result is cached_tree
        service.comment_repo.get_tree.assert_not_called()

    def test_cache_miss_queries_repo_builds_tree_and_caches_result(self, service):
        """On cache miss: call repo, build nested tree, store in cache, return tree."""
        flat_rows = [
            {
                "id": "root-id",
                "parent_id": None,
                "text": "hi",
                "created_at": None,
                "username": "u",
                "email": "e@e.com",
                "home_page": None,
                "depth": 0,
                "path": ["root-id"],
                "attachment_type": None,
                "attachment_filename": None,
                "attachment_path": None},
        ]
        service.comment_repo.get_tree.return_value = flat_rows

        with (
            patch("django.core.cache.cache.get", return_value=None),
            patch("django.core.cache.cache.set") as mock_set
        ):
            result = service.get_tree("root-id")

        assert len(result) == 1
        assert result[0]["id"] == "root-id"
        mock_set.assert_called_once()

    def test_cache_miss_with_empty_repo_raises_not_found(self, service):
        """If the repo returns nothing (root_id doesn't exist), raise NotFoundError."""
        service.comment_repo.get_tree.return_value = []

        with (
            patch("django.core.cache.cache.get", return_value=None),
            patch("django.core.cache.cache.set")
        ):
            with pytest.raises(NotFoundError):
                service.get_tree("nonexistent-id")
