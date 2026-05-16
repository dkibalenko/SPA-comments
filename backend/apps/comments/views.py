import logging

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.attachments.services import AttachmentService
from apps.comments.filters import CommentFilter
from apps.comments.serializers import (
    CommentCreateSerializer,
    CommentListSerializer,
    CommentTreeSerializer,
)
from apps.comments.services import CommentService
from core.cache import COMMENT_LIST_TTL, make_list_cache_key
from core.exceptions import (
    CaptchaError,
    FileTooLargeError,
    NotFoundError,
    UnsupportedFileTypeError,
    ValidationError,
)
from core.pagination import CommentPagination

log = logging.getLogger(__name__)


class CommentViewSet(CreateModelMixin, ListModelMixin, GenericViewSet):
    """Main comments endpoint. Handles HTTP concerns only.

    Inherits CreateModelMixin  → POST /api/comments/
    Inherits ListModelMixin    → GET  /api/comments/
    Custom action              → GET  /api/comments/{id}/tree/
    """

    pagination_class = CommentPagination
    filterset_class = CommentFilter

    def __init__(self, service=None, attachment_service=None, **kwargs):
        super().__init__(**kwargs)
        self.service = service or CommentService()
        self.attachment_service = attachment_service or AttachmentService()

    def get_queryset(self):
        """Return top-level queryset for list + filter + paginate flow."""
        return self.service.get_top_level_queryset()

    def get_serializer_class(self):
        """Return the right serializer per action."""
        if self.action == "create":
            return CommentCreateSerializer
        return CommentListSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create a new comment or reply with optional file attachment.

        Accepts multipart/form-data so file + fields arrive together.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # return default HTTP 400
        data = serializer.validated_data

        try:
            result = self.service.create_comment(
                username=data["username"],
                email=data["email"],
                text=data["text"],
                ip_address=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                captcha_token=data["captcha_token"],
                captcha_answer=data["captcha_answer"],
                home_page=data.get("home_page"),
                parent_id=str(data["parent_id"])
                if data.get("parent_id")
                else None,
            )
        except (ValidationError, CaptchaError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = result["comment"]
        token = result["token"]

        # optional file attachment
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            try:
                self.attachment_service.handle_upload(
                    comment_id=str(comment.id),  # type: ignore
                    file=uploaded_file,
                )
            except (UnsupportedFileTypeError, FileTooLargeError) as exc:
                # rollback to keep atomicity
                comment.delete()  # type: ignore
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {
                "id": str(comment.id),  # type: ignore
                "created_at": comment.created_at,  # type: ignore
                "token": token,  # frontend stores token for next submission
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        """Paginated sortable list - served from cache when available.

        Cache key encodes ordering + page, so each unique combination
        gets its own cache entry.
        """
        # build cache key from the actual request params
        ordering = request.query_params.get("ordering", "-created_at")
        page = request.query_params.get("page", "1")
        cache_key = make_list_cache_key(ordering=ordering, page=page)

        # try cache first
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            log.debug(f"Cache HIT: list ordering={ordering} page={page}")
            return Response(cached_response)

        log.debug(f"Cache MISS: list ordering={ordering} page={page}")

        # cache miss - build response normally
        queryset = self.filter_queryset(
            self.get_queryset()
        )  # applies CommentFilter
        page_obj = self.paginate_queryset(queryset)  # slices the DB query

        # for absolute URL generation in AttachmentSerializer
        serializer_context = {"request": request}

        if page_obj is not None:
            serializer = CommentListSerializer(
                page_obj, many=True, context=serializer_context
            )
            # wrap the data in {count, next, previous, results}
            response_data = self.get_paginated_response(serializer.data).data
        else:
            serializer = CommentListSerializer(
                queryset, many=True, context=serializer_context
            )
            response_data = serializer.data

        # store in cache
        cache.set(cache_key, response_data, timeout=COMMENT_LIST_TTL)

        return Response(response_data)

    @action(detail=True, methods=["get"], url_path="tree")
    def tree(self, request: Request, pk: str) -> Response:
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
