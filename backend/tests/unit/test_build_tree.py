import pytest

from apps.comments.services import CommentService


def make_row(id: str, parent_id=None, **extras) -> dict:
    """Build a minimal flat CTE row dict accepted by _build_tree.

    Only `id` and `parent_id` drive tree construction; the rest is
    pass-through payload that should appear unchanged in the output.
    """
    return {
        "id": id,
        "parent_id": parent_id,
        "text": "test text",
        "created_at": "2026-01-01T00:00:00",
        "username": "testuser",
        "email": "test@example.com",
        "home_page": None,
        "depth": 0,
        "path": [id],
        "attachment_type": None,
        "attachment_filename": None,
        "attachment_path": None,
        **extras,
    }


@pytest.fixture
def service():
    """CommentService instantiated with real (no-op) default dependencies.

    _build_tree is a pure O(n) dict transformation — it does not touch
    the database, Redis, or any I/O. No @pytest.mark.django_db needed.
    """
    return CommentService()


class TestBuildTree:

    def test_empty_input_returns_empty_list(self, service):
        assert service._build_tree([]) == []

    def test_single_root_has_empty_replies(self, service):
        result = service._build_tree([make_row("root")])

        assert len(result) == 1
        assert result[0]["id"] == "root"
        assert result[0]["replies"] == []  # _build_tree injects "replies": [] into every node

    def test_root_with_one_reply(self, service):
        rows = [
            make_row("root"),
            make_row("child", parent_id="root", depth=1),
        ]
        result = service._build_tree(rows)

        assert len(result) == 1
        assert len(result[0]["replies"]) == 1
        assert result[0]["replies"][0]["id"] == "child"

    def test_root_with_two_sibling_replies_preserves_order(self, service):
        rows = [
            make_row("root"),
            make_row("child1", parent_id = "root", depth =1 ),
            make_row("child2", parent_id = "root", depth = 1),
        ]
        result = service._build_tree(rows)

        reply_ids = [r["id"] for r in result[0]["replies"]]
        assert reply_ids == ["child1", "child2"]

    def test_three_level_deep_chain(self, service):
        rows = [
            make_row("a", depth=0),
            make_row("b", parent_id="a", depth=1),
            make_row("c", parent_id="b", depth=2),
        ]
        result = service._build_tree(rows)

        root = result[0]
        child = root["replies"][0]
        grandchild = child["replies"][0]

        assert root["id"] == "a"
        assert child["id"] == "b"
        assert grandchild["id"] == "c"
        assert grandchild["replies"] == []

    def test_multiple_roots_no_replies(self, service):
        rows = [make_row("root1"), make_row("root2")]
        result = service._build_tree(rows)

        assert len(result) == 2
        assert result[0]["id"] == "root1"
        assert result[1]["id"] == "root2"

    def test_multiple_roots_each_with_own_reply(self, service):
        rows = [
            make_row("r1"),
            make_row("r1-child", parent_id="r1", depth=1),
            make_row("r2"),
            make_row("r2-child", parent_id="r2", depth=1),
        ]
        result = service._build_tree(rows)

        assert len(result) == 2
        assert result[0]["replies"][0]["id"] == "r1-child"
        assert result[1]["replies"][0]["id"] == "r2-child"

    def test_orphaned_child_is_silently_dropped(self, service):
        """A node whose parent_id references a missing node must not appear."""
        rows = [
            make_row("root"),
            make_row("orphan", parent_id="does-not-exist"),
        ]
        result = service._build_tree(rows)

        assert len(result) == 1
        assert result[0]["replies"] == []

    def test_every_node_has_replies_key(self, service):
        """All nodes — roots and leaves alike — must have a 'replies' list."""
        rows = [
            make_row("root"),
            make_row("child", parent_id="root"),
        ]
        result = service._build_tree(rows)

        root  = result[0]
        child = root["replies"][0]
        assert "replies" in root
        assert "replies" in child
        assert isinstance(child["replies"], list)

    def test_original_row_fields_passed_through(self, service):
        """_build_tree must not drop or mutate payload fields."""
        rows = [make_row("root", text="Custom text", username="alice")]
        result = service._build_tree(rows)

        node = result[0]
        assert node["text"] == "Custom text"
        assert node["username"] == "alice"
        assert node["id"] == "root"

    @pytest.mark.parametrize(
        "tree_shape, expected_root_count, expected_depth",
        [
            # (rows, expected roots, depth of deepest node)
            ([make_row("r")], 1, 0),
            ([make_row("r"), make_row("c", parent_id="r", depth=1)], 1, 1),
            ([make_row("r1"), make_row("r2")], 2, 0),
            (
                [
                    make_row("r"),
                    make_row("c",  parent_id="r",  depth=1),
                    make_row("gc", parent_id="c",  depth=2),
                ],
                1, 2,
            ),
        ]
    )
    def test_tree_shapes(self, service, tree_shape, expected_root_count, expected_depth):
        """
        Checks two structural properties - root count and maximum nesting depth
        across four tree main shapes.
        """
        result = service._build_tree(tree_shape)
        assert len(result) == expected_root_count

        def max_depth(nodes, current=0):
            """Traverses the output tree and returns the deepest level."""
            if not nodes:
                return current - 1
            depths = []
            for n in nodes:
                depth = max_depth(n["replies"], current + 1)
                depths.append(depth)
            return max(depths)

        assert max_depth(result) == expected_depth
