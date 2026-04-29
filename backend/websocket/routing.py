from django.urls import path

from websocket.consumers import CommentConsumer


websocket_urlpatterns = [
    path("ws/comments/", CommentConsumer.as_asgi()),
]
