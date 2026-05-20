import logging

from django.core.cache import cache
from django.db import transaction

from apps.captcha_app.services import CaptchaService
from apps.comments.models import Comment
from apps.comments.repository import CommentRepository
from apps.comments.signals import comment_created
from apps.users.jwt import issue_identity_token
from apps.users.repository import UserRepository
from core.cache import (
    COMMENT_TREE_TTL,
    invalidate_list_cache,
    invalidate_tree_cache,
    make_tree_cache_key,
)
from core.exceptions import NotFoundError, ValidationError
from core.validators import sanitize_comment_text

log = logging.getLogger(__name__)


class CommentService:
    """Business logic layer for the comment domain.

    Orchestrates: user identity → text sanitization → comment creation
    → side effects (signals, notifications).
    """

    def __init__(
        self,
        comment_repo: CommentRepository | None = None,
        user_repo: UserRepository | None = None,
        captcha_service: CaptchaService | None = None,
    ) -> None:
        self.comment_repo = comment_repo or CommentRepository()
        self.user_repo = user_repo or UserRepository()
        self.captcha_service = captcha_service or CaptchaService()

    def create_comment(
        self,
        username: str,
        email: str,
        text: str,
        ip_address: str,
        user_agent: str,
        captcha_token: str,
        captcha_answer: str,
        home_page: str | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Comment | str]:
        """Create a comment and return it with an identity token for the user.

        Steps:
            1. Validate CAPTCHA response
            2. Sanitize and validate comment text (XSS protection)
            3. Validate parent exists if `parent_id` provided
            4. Resolve user identity (get or create)
            5. Persist the comment
            6. Reload with user relation for signal payload
            7. Invalidate cache
            8. Fire `comment_created` signal. Issue identity token for the user

        :raises ValidationError: If `text` is empty after sanitization,
                                 or `parent_id` doesn't exist.
        :returns: Dict containing the created comment and an identity token
            for the user.
        """
        self.captcha_service.validate(captcha_token, captcha_answer)

        clean_text = sanitize_comment_text(text)
        if not clean_text.strip():
            raise ValidationError("Comment text cannot be empty.")

        if parent_id:
            parent = self.comment_repo.get_by_id(parent_id)
            if not parent:
                raise ValidationError(
                    f"Parent comment {parent_id} does not exist."
                )

        user, _ = self.user_repo.get_or_create_by_identity(
            username=username,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            home_page=home_page,
        )

        comment = self.comment_repo.create(
            user_id=user.id,
            text=clean_text,
            parent_id=parent_id,
        )

        comment = self.comment_repo.get_by_id(comment.id)  # type: ignore

        if parent_id:
            root_id = self._find_root_id(parent_id)
            invalidate_tree_cache(root_id)
            invalidate_list_cache()
            log.debug(
                f"Invalidated tree cache for root {root_id} and list cache"
            )
        else:
            invalidate_list_cache()
            log.debug("Invalidated list cache")

        token = issue_identity_token(user)
        comment_ref = comment

        transaction.on_commit(
            lambda: comment_created.send(
                sender=self.__class__,
                comment=comment_ref,
            )
        )

        return {"comment": comment, "token": token}

    def _find_root_id(self, comment_id: str) -> str:
        """Walk up the parent chain to find the thread root.

        Iterates upward until a comment with no parent is found.
        That comment's id is the cache key for the whole thread.
        Used to invalidate the correct tree cache key.
        """
        current_id = comment_id
        visited = set()

        while True:
            if current_id in visited:
                log.warning(f"Cycle detected in comment chain at {current_id}")
                return current_id

            visited.add(current_id)

            comment = self.comment_repo.get_by_id(current_id)

            if not comment or not comment.parent_id:
                return current_id

            current_id = str(comment.parent_id)

    def get_tree(self, root_id: str) -> list[dict]:
        """Fetch full thread and build nested structure.

        Fetch tree - from cache if available, DB otherwise.

        :raises NotFoundError: If `root_id` doesn't exist.
        :returns: Nested list of dicts representing the comment tree.
        """
        cache_key = make_tree_cache_key(root_id)

        cached = cache.get(cache_key)
        if cached is not None:
            log.debug(f"Cache HIT: tree {root_id}")
            return cached

        log.debug(f"Cache MISS: tree {root_id}")
        flat_rows = self.comment_repo.get_tree(root_id)

        if not flat_rows:
            raise NotFoundError(f"Comment {root_id} not found.")

        tree = self._build_tree(flat_rows)

        cache.set(cache_key, tree, timeout=COMMENT_TREE_TTL)
        return tree

    def get_top_level_queryset(self):
        """Expose the top-level queryset for the view's filter+paginate flow"""
        return self.comment_repo.get_top_level_queryset()

    @staticmethod
    def _build_tree(flat_rows: list[dict]) -> list[dict]:
        """Convert flat CTE result into nested dict structure.

        O(n) - single pass. Every node is indexed by id first,
        then each node is attached to its parent's replies list.

        :param `flat_rows`: Ordered flat list from `get_tree()` CTE.
        :returns: List containing only root nodes, with nested replies.
        """
        nodes: dict[str, dict] = {}

        for row in flat_rows:
            node = {**row, "replies": []}
            nodes[str(row["id"])] = node

        roots: list[dict] = []

        for row in flat_rows:
            node = nodes[str(row["id"])]
            if row["parent_id"] is None:
                roots.append(node)
            else:
                parent = nodes.get(str(row["parent_id"]))
                if parent:
                    # orphan is never appended anywhere
                    parent["replies"].append(node)

        return roots
