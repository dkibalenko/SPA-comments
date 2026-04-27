from apps.captcha_app.services import CaptchaService
from apps.comments.models import Comment
from apps.comments.repository import CommentRepository
from apps.users.repository import UserRepository
from core.exceptions import NotFoundError, ValidationError
from core.validators import sanitize_comment_text


class CommentService:
    """Business logic layer for the comment domain.

    Orchestrates: user identity → text sanitization → comment creation
    → side effects (signals, notifications).
    """

    def __init__(
        self,
        comment_repo: CommentRepository | None = None,
        user_repo: UserRepository | None = None,
        captcha_service: CaptchaService | None = None
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
    ) -> Comment:
        """Create a comment, resolving user identity first.

        Steps:
            1. Validate CAPTCHA response
            2. Sanitize and validate comment text (XSS protection)
            3. Validate parent exists if `parent_id` provided
            4. Resolve user identity (get or create)
            5. Persist the comment

        :raises ValidationError: If `text` is empty after sanitization,
                                 or `parent_id` doesn't exist.
        :returns: Saved `Comment` instance.
        """
        # 1. CAPTCHA first
        self.captcha_service.validate(captcha_token, captcha_answer)

        # 2. sanitize text
        clean_text = sanitize_comment_text(text)
        if not clean_text.strip():
            raise ValidationError("Comment text cannot be empty.")

        # 3. validate parent
        if parent_id:
            parent = self.comment_repo.get_by_id(parent_id)
            if not parent:
                raise ValidationError(
                    f"Parent comment {parent_id} does not exist."
                )

        # 4. resolve user identity
        user, _ = self.user_repo.get_or_create_by_identity(
            username=username,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            home_page=home_page,
        )

        # 5. persist
        comment = self.comment_repo.create(
            user_id=user.id,
            text=clean_text,
            parent_id=parent_id,
        )

        return comment

    def get_tree(self, root_id: str) -> list[dict]:
        """Fetch full thread and build nested structure.

        :raises NotFoundError: If `root_id` doesn't exist.
        :returns: Nested list of dicts representing the comment tree.
        """
        flat_rows = self.comment_repo.get_tree(root_id)

        if not flat_rows:
            raise NotFoundError(f"Comment {root_id} not found.")

        return self._build_tree(flat_rows)

    def get_top_level_queryset(self):
        """Expose the top-level queryset for the view's filter+paginate flow"""
        return self.comment_repo.get_top_level_queryset()

    def _build_tree(self, flat_rows: list[dict]) -> list[dict]:
        """Convert flat CTE result into nested dict structure.

        O(n) — single pass. Every node is indexed by id first,
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
                    parent["replies"].append(node)

        return roots
