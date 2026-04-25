from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.comments.filters import CommentFilter
from apps.comments.serializers import (
    CommentCreateSerializer,
    CommentListSerializer,
    CommentTreeSerializer,
)
from apps.comments.services import CommentService
from core.exceptions import NotFoundError, ValidationError
from core.pagination import CommentPagination


class CommentViewSet(CreateModelMixin, ListModelMixin, GenericViewSet):
    """Main comments endpoint. Handles HTTP concerns only.

    Inherits CreateModelMixin  → POST /api/comments/
    Inherits ListModelMixin    → GET  /api/comments/
    Custom action              → GET  /api/comments/{id}/tree/ 
    """
    pagination_class = CommentPagination
    filterset_class = CommentFilter

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = CommentService()

    def get_queryset(self):
        """Return top-level queryset for list + filter + paginate flow."""
        return self.service.get_top_level_queryset()

    def get_serializer_class(self):
        """Return the right serializer per action."""
        if self.action == "create":
            return CommentCreateSerializer
        return CommentListSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create a new comment or reply."""
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            comment = self.service.create_comment(
                username=data["username"],
                email=data["email"],
                text=data["text"],
                ip_address=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                home_page=data.get("home_page"),
                parent_id=str(data["parent_id"]) if data.get(
                    "parent_id"
                ) else None
            )
        except ValidationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"id": str(comment.id), "created_at": comment.created_at},
            status=status.HTTP_201_CREATED,
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        """Paginated, sortable list of top-level comments."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = CommentListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CommentListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="tree")
    def tree(self, request: Request, pk: str = None) -> Response:
        """Return the full nested reply tree for a single comment."""
        try:
            tree_data = self.service.get_tree(root_id=pk)
        except NotFoundError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CommentTreeSerializer(tree_data, many=True)
        return Response(serializer.data)
