from django.urls import path  # pragma: no cover

from websocket.consumers import CommentConsumer  # pragma: no cover

websocket_urlpatterns = [  # pragma: no cover
    path("ws/comments/", CommentConsumer.as_asgi()),
]
