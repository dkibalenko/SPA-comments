from django.db import connection
from django.db.models import Count
from django.db.models.functions import Lower

from apps.comments.models import Comment


class CommentRepository:
    """All database operations for Comments.

    Top-level list uses Django ORM (clean, readable, filterable).
    Tree fetch uses raw recursive CTE (necessary for arbitrary depth).
    """

    def create(
        self,
        user_id: str,
        text: str,
        parent_id: str | None = None,
    ) -> Comment:
        """Insert a new comment row. Returns the saved instance."""
        return Comment.objects.create(
            user_id=user_id,
            text=text,
            parent_id=parent_id,
        )

    def get_by_id(self, comment_id: str) -> Comment | None:
        """Fetch single comment with its user. `None` if not found."""
        try:
            return (
                Comment.objects
                .select_related("user")
                .get(id=comment_id)
            )
        except Comment.DoesNotExist:
            return None

    def get_top_level_queryset(self):
        """Return a non-evaluated queryset of top-level comments only.

        Annotated with `reply_count`, `username_lower` and ordered by
        `created_at` desc.
        """
        return (
            Comment.objects
            .filter(parent__isnull=True)
            .select_related("user", "attachment")
            .annotate(
                reply_count=Count("replies"),
                # LOWER(users_user.username) in SELECT
                username_lower=Lower("user__username"),
            )
            .order_by("-created_at")
        )

    def get_tree(self, root_id: str) -> list[dict]:
        """Fetch an entire comment thread in one recursive CTE query.

        Returns a flat list of dicts ordered by `path` - an array
        that encodes the ancestry of each node. Sorting by path
        gives correct visual tree order (parent always before children,
        siblings in chronological order).

        The Service layer builds the nested structure from this flat result.

        :param root_id: UUID of the top-level comment to expand.
        :returns: Flat list of row dicts, tree-ordered by path.
        """
        sql = """
            WITH RECURSIVE comment_tree AS (

                -- ANCHOR: start with the requested root comment
                SELECT
                    c.id,
                    c.parent_id,
                    c.text,
                    c.created_at,
                    u.username,
                    u.email,
                    u.home_page,
                    0                    AS depth,
                    ARRAY[c.id::text]    AS path,  --chronological tree order ([root_id, child_id, gchild_id..])
                    a.file_type          AS attachment_type,
                    a.original_filename  AS attachment_filename,
                    a.storage_path       AS attachment_path
                FROM comments_comment c
                JOIN users_user u ON c.user_id = u.id
                LEFT JOIN attachments_attachment a ON a.comment_id = c.id
                WHERE c.id = %s

                UNION ALL

                -- RECURSIVE MEMBER: children of nodes already in the CTE
                SELECT
                    c.id,
                    c.parent_id,
                    c.text,
                    c.created_at,
                    u.username,
                    u.email,
                    u.home_page,
                    ct.depth + 1,
                    ct.path || c.id::text,
                    a.file_type,
                    a.original_filename,
                    a.storage_path
                FROM comments_comment c
                JOIN users_user u ON c.user_id = u.id
                LEFT JOIN attachments_attachment a ON a.comment_id = c.id
                INNER JOIN comment_tree ct ON c.parent_id = ct.id
                WHERE ct.depth < 50      -- guard against pathological data

            )
            SELECT * FROM comment_tree ORDER BY path;
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params=[str(root_id)])  # pass param to %s
            columns = [col[0] for col in cursor.description]  # e.g [('id', ...),] -> extract only names, [0]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

# columns = [
#     'id',
#     'parent_id',
#     'text',
#     'created_at',
#     'username',
#     'email',
#     'home_page',
#     'depth',
#     'path'
# ]
# cursor.fetchall() ->
# [
#     (
#         'root-id',
#         None,
#         'Root comment text',
#         datetime(...),
#         'alice',
#         'alice@example.com',
#         'https://alice.com',
#         0,
#         ['root-id']
#     ),
#     ...
# ]
# dict(zip(..)) ->
# [{
#     'id': 'root-id',
#     'parent_id': None,
#     'text': 'Root comment text',
#     'created_at': datetime(...),
#     'username': 'alice',
#     'email': 'alice@example.com',
#     'home_page': 'https://alice.com',
#     'depth': 0,
#     'path': ['root-id']
# },]
