from rest_framework.routers import DefaultRouter

from apps.comments.views import CommentViewSet

router = DefaultRouter()
router.register(r"comments", CommentViewSet, basename="comments")

urlpatterns = router.urls
