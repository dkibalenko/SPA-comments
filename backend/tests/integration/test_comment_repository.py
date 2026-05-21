import uuid

import pytest

from apps.comments.repository import CommentRepository
from tests.factories import CommentFactory, UserFactory


@pytest.mark.django_db
class TestGetTree:
    """Tests for `CommentRepository.get_tree()`,
    which fetches an entire comment thread in one query using a recursive CTE.

    These tests verify the SQL is correct: `depth` is computed right,
    `path` array is built correctly, joins work, and the ordering is deterministic.
    """

    def test_root_comment_returns_one_row(self):
        """Sanity check that a single comment is returned as one row."""
        comment = CommentFactory()
        rows = CommentRepository().get_tree(str(comment.id))
        assert len(rows) == 1

    def test_root_row_has_correct_id_and_depth(self):
        """Test that the root comment's ID and depth are correct in the result."""
        comment = CommentFactory()
        row = CommentRepository().get_tree(str(comment.id))[0]
        assert str(row["id"]) == str(comment.id)
        assert row["depth"] == 0
        assert row["parent_id"] is None

    def test_reply_included_with_depth_one(self):
        """Test that a reply to the root comment is included in the result with depth 1."""
        parent = CommentFactory()
        child = CommentFactory(parent=parent)
        rows = CommentRepository().get_tree(str(parent.id))
        assert len(rows) == 2
        by_id = {str(r["id"]): r for r in rows}
        assert by_id[str(child.id)]["depth"] == 1

    def test_three_level_chain_depths(self):
        """Test that depth is correctly computed for a chain of 3 comments.
        
        This verifies the recursive CTE is correctly adding 1 to the depth of the parent.
        This proves the `UNION ALL` recurses twice and that `ct.depth + 1`
        accumulates correctly across iterations.
        All three depths are asserted to catch an off-by-one that might only appear at level 2.
        """
        root = CommentFactory()
        child = CommentFactory(parent=root)
        grandchild = CommentFactory(parent=child)
        rows = CommentRepository().get_tree(str(root.id))
        by_id = {str(r["id"]): r for r in rows}
        assert by_id[str(root.id)]["depth"] == 0
        assert by_id[str(child.id)]["depth"] == 1
        assert by_id[str(grandchild.id)]["depth"] == 2

    def test_path_encodes_full_ancestry(self):
        """Test that the `path` field in the result correctly encodes the ancestry of each comment."""
        root = CommentFactory()
        child = CommentFactory(parent=root)
        grandchild = CommentFactory(parent=child)
        rows = CommentRepository().get_tree(str(root.id))
        by_id = {str(r["id"]): r for r in rows}
        assert by_id[str(grandchild.id)]["path"] == [
            str(root.id), str(child.id), str(grandchild.id)
        ]

    def test_nonexistent_id_returns_empty_list(self):
        """Test that requesting a tree for a non-existent root ID returns an empty list, not an error."""
        rows = CommentRepository().get_tree(str(uuid.uuid4()))
        assert rows == []

    def test_null_attachment_fields_when_no_attachment(self):
        """Test that the attachment fields in the result are null when a comment has no attachment."""
        comment = CommentFactory()
        row = CommentRepository().get_tree(str(comment.id))[0]
        assert row["attachment_type"] is None
        assert row["attachment_filename"] is None
        assert row["attachment_path"] is None

    def test_rows_include_user_fields(self):
        """Test that the rows returned by `get_tree` include the expected user fields."""
        # use specific username/email rather than factory generates
        user = UserFactory(username="charlie", email="charlie@example.com")
        comment = CommentFactory(user=user)
        row = CommentRepository().get_tree(str(comment.id))[0]
        assert row["username"] == "charlie"
        assert row["email"] == "charlie@example.com"

    def test_root_appears_before_children_in_result(self):
        """Test that the root comment appears before its children in the result list, verifying correct ordering by `path`.

        The service's `_build_tree()` method processes rows in this order and
        depends on parents appearing before children to attach replies correctly.
        """
        root = CommentFactory()
        CommentFactory(parent=root)
        CommentFactory(parent=root)
        rows = CommentRepository().get_tree(str(root.id))
        assert str(rows[0]["id"]) == str(root.id)


@pytest.mark.django_db
class TestGetTopLevelQueryset:

    def test_returns_only_top_level_comments(self):
        """Test that `get_top_level_queryset` returns only comments with no parent (top-level comments)."""
        top = CommentFactory()
        CommentFactory(parent=top)  # reply must be excluded
        qs = CommentRepository().get_top_level_queryset()
        assert qs.count() == 1
        assert qs.first().id == top.id

    def test_reply_count_annotation(self):
        """Test that the `reply_count` annotation correctly counts the number of replies for each top-level comment."""
        top = CommentFactory()
        CommentFactory(parent=top)
        CommentFactory(parent=top)
        qs = CommentRepository().get_top_level_queryset()
        assert qs.first().reply_count == 2

    def test_comment_with_no_replies_has_reply_count_zero(self):
        """Test that a top-level comment with no replies has a `reply_count` of zero."""
        CommentFactory()
        qs = CommentRepository().get_top_level_queryset()
        assert qs.first().reply_count == 0

    def test_username_lower_annotation_is_lowercase(self):
        """Test that the `username_lower` annotation correctly converts the username to lowercase."""
        user = UserFactory(username="ALICE", email="alice@example.com")
        CommentFactory(user=user)
        qs = CommentRepository().get_top_level_queryset()
        assert qs.first().username_lower == "alice"

    def test_default_order_is_newest_first(self):
        """Test that the default ordering of `get_top_level_queryset` is by newest comments first."""
        older = CommentFactory()
        newer = CommentFactory()
        qs = CommentRepository().get_top_level_queryset()
        ids = list(qs.values_list("id", flat=True))
        assert ids[0] == newer.id
        assert ids[1] == older.id
