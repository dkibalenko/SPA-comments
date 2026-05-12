import uuid
from unittest.mock import patch

import pytest

from apps.comments.models import Comment
from core.exceptions import CaptchaError
from tests.factories import CommentFactory, UserFactory


COMMENTS_URL = "/api/comments/"


def _payload(**overrides):
    data = {
        "username": "alice",
        "email": "alice@example.com",
        "text": "Hello <strong>world</strong>",
        "captcha_token": "tok",
        "captcha_answer": "ans",
    }
    data.update(overrides)
    return data


# POST /api/comments/

@pytest.mark.django_db
class TestCommentCreate:

    def test_happy_path_returns_201(self, api_client, bypass_captcha):
        """Tests that a well-formed request with valid captcha creates a comment and returns 201."""
        resp = api_client.post(COMMENTS_URL, _payload())
        assert resp.status_code == 201

    def test_response_contains_id_and_token(self, api_client, bypass_captcha):
        """Tests that the create response contains the new comment's ID and token.

        The frontend needs the ID to know where to display the new comment,
        and the token to authenticate subsequent submissions.
        If the view accidentally returned {} with a 201, this test would catch that.
        """
        resp = api_client.post(COMMENTS_URL, _payload())
        assert "id" in resp.data
        assert "token" in resp.data

    def test_comment_row_persisted(self, api_client, bypass_captcha):
        """Tests that a comment row is actually created in the database after a successful create request.
        
        This test hits the database directly and confirms the row exists. If the view had a bug where it returned 201 without saving, this test would catch that.
        """
        resp = api_client.post(COMMENTS_URL, _payload())
        assert Comment.objects.filter(id=resp.data["id"]).exists()

    def test_wrong_captcha_returns_400(self, api_client):
        """Tests that if the captcha validation fails, the API returns a 400 with an appropriate error message."""
        with patch(
            "apps.captcha_app.services.CaptchaService.validate",
            side_effect=CaptchaError("expired"),
        ):
            resp = api_client.post(COMMENTS_URL, _payload())
        assert resp.status_code == 400

    def test_xss_script_tag_stripped_from_stored_text(self, api_client, bypass_captcha):
        """
        Tests that if the comment text contains a script tag, it is stripped out
        before saving to the database, but the rest of the text is preserved.
        """
        resp = api_client.post(
            COMMENTS_URL, _payload(text="<script>evil()</script>Hello")
        )
        assert resp.status_code == 201
        stored = Comment.objects.get(id=resp.data["id"])
        assert "<script>" not in stored.text
        assert "Hello" in stored.text

    def test_allowed_html_preserved(self, api_client, bypass_captcha):
        """Tests that allowed HTML tags are preserved in the stored comment text."""
        resp = api_client.post(
            COMMENTS_URL, _payload(text="<strong>bold</strong>")
        )
        assert resp.status_code == 201
        stored = Comment.objects.get(id=resp.data["id"])
        assert "<strong>bold</strong>" in stored.text

    def test_nonexistent_parent_returns_400(self, api_client, bypass_captcha):
        """
        Tests that if the parent_id references a comment that doesn't exist,
        the API returns a 400 with an appropriate error message.
        """
        resp = api_client.post(COMMENTS_URL, _payload(parent_id=str(uuid.uuid4())))
        assert resp.status_code == 400

    def test_reply_links_to_parent_in_db(self, api_client, bypass_captcha):
        """
        Tests that if a comment is created with a valid parent_id, the resulting
        comment row in the database has its parent_id field set to the correct value,
        establishing the parent-child relationship.
        """
        parent = CommentFactory()
        resp = api_client.post(COMMENTS_URL, _payload(parent_id=str(parent.id)))
        assert resp.status_code == 201
        child = Comment.objects.get(id=resp.data["id"])
        assert str(child.parent_id) == str(parent.id)

    def test_missing_username_returns_400(self, api_client, bypass_captcha):
        """
        Tests that if the username field is missing from the request payload,
        the API returns a 400 with an appropriate error message.

        This test confirms the serializer-level validation catches missing required fields.
        """
        payload = _payload()
        del payload["username"]
        resp = api_client.post(COMMENTS_URL, payload)
        assert resp.status_code == 400

    def test_invalid_username_chars_returns_400(self, api_client, bypass_captcha):
        """
        Tests that if the username field contains invalid characters,
        the API returns a 400 with an appropriate error message.
        """
        resp = api_client.post(COMMENTS_URL, _payload(username="alice!"))
        assert resp.status_code == 400

    def test_invalid_email_returns_400(self, api_client, bypass_captcha):
        """
        Tests that if the email field contains an invalid format,
        the API returns a 400 with an appropriate error message.
        """
        resp = api_client.post(COMMENTS_URL, _payload(email="not-an-email"))
        assert resp.status_code == 400


# GET /api/comments/

@pytest.mark.django_db
class TestCommentList:

    def test_empty_db_returns_200_with_zero_count(
        self, api_client, use_local_memory_cache
    ):
        """
        Tests that if there are no comments in the database, the API returns
        a 200 with count=0.

        This is the baseline: the endpoint exists, the pagination wrapper is
        present, and an empty result set is not an error
        """
        resp = api_client.get(COMMENTS_URL)
        assert resp.status_code == 200
        assert resp.data["count"] == 0

    def test_top_level_comment_appears_in_list(
        self, api_client, use_local_memory_cache
    ):
        """
        Tests that if there is a top-level comment in the database, it appears
        in the list response with count=1.
        """
        CommentFactory()
        resp = api_client.get(COMMENTS_URL)
        assert resp.data["count"] == 1

    def test_replies_excluded_from_list(self, api_client, use_local_memory_cache):
        """
        Tests that if there is a comment with a reply, only the top-level
        comment appears in the list response, and the reply does not affect
        the count."""
        top = CommentFactory()
        CommentFactory(parent = top)  # reply
        resp = api_client.get(COMMENTS_URL)
        assert resp.data["count"] == 1

    def test_ordering_by_username_ascending(
        self, api_client, use_local_memory_cache
    ):
        """
        Tests that if there are multiple comments by different users, when we
        request ordering by username ascending, the results are sorted alphabetically by username."""
        user_z = UserFactory(username = "zara", email = "zara@example.com")
        user_a = UserFactory(username = "alice", email = "alice@example.com")
        CommentFactory(user = user_z)
        CommentFactory(user = user_a)
        resp = api_client.get(COMMENTS_URL + "?ordering=username")
        assert resp.status_code == 200
        usernames = [item["user"]["username"] for item in resp.data["results"]]
        assert usernames == sorted(usernames, key = str.lower)

    def test_ordering_by_date_descending(self, api_client, use_local_memory_cache):
        """
        Tests that if there are multiple comments with different creation dates,
        when we request ordering by date descending, the results are sorted with
        newest comments first.
        """
        c1 = CommentFactory()
        c2 = CommentFactory()
        resp = api_client.get(COMMENTS_URL + "?ordering=-date")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.data["results"]]
        # newest (c2) first
        assert str(ids[0]) == str(c2.id)
        assert str(ids[1]) == str(c1.id)

    def test_response_shape_contains_expected_fields(
        self, api_client, use_local_memory_cache
    ):
        """
        The contract test. Tests that the shape of each comment item in the response
        the frontend depends on contains the expected fields.
        """
        CommentFactory()
        resp = api_client.get(COMMENTS_URL)
        item = resp.data["results"][0]
        for field in ("id", "user", "text", "created_at", "reply_count"):
            assert field in item


# GET /api/comments/{id}/tree/

@pytest.mark.django_db
class TestCommentTree:

    def test_existing_root_returns_200(self, api_client, use_local_memory_cache):
        """Tests that an existing root comment returns a 200."""
        root = CommentFactory()
        resp = api_client.get(f"{COMMENTS_URL}{root.id}/tree/")
        assert resp.status_code == 200

    def test_root_node_in_response(self, api_client, use_local_memory_cache):
        """Tests that the response contains the root node with expected ID."""
        root = CommentFactory()
        resp = api_client.get(f"{COMMENTS_URL}{root.id}/tree/")
        assert len(resp.data) == 1
        assert str(resp.data[0]["id"]) == str(root.id)

    def test_reply_nested_under_root(self, api_client, use_local_memory_cache):
        """
        The core structural test. Tests that if a comment has a reply,
        the reply appears in the "replies" list of the root comment in the response,
        with the correct ID.
        This test would fail if `_build_tree` returned all nodes flat or put
        the child in the wrong parent's replies.
        """
        root = CommentFactory()
        child = CommentFactory(parent=root)
        resp = api_client.get(f"{COMMENTS_URL}{root.id}/tree/")
        assert len(resp.data[0]["replies"]) == 1
        assert str(resp.data[0]["replies"][0]["id"]) == str(child.id)

    def test_depth_field_in_response(self, api_client, use_local_memory_cache):
        """
        Tests that each node in the response contains a "depth" field indicating
        its depth in the tree, with root at depth 0, its children at depth 1, etc.
        """
        root = CommentFactory()
        child = CommentFactory(parent=root)
        resp = api_client.get(f"{COMMENTS_URL}{root.id}/tree/")
        assert resp.data[0]["depth"] == 0
        assert resp.data[0]["replies"][0]["depth"] == 1

    def test_nonexistent_root_returns_404(self, api_client, use_local_memory_cache):
        """
        Tests that if the root comment ID doesn't exist, the API returns a 404
        with an appropriate error message.
        """
        resp = api_client.get(f"{COMMENTS_URL}{uuid.uuid4()}/tree/")
        assert resp.status_code == 404
