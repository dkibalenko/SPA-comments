import asyncio

from django.test import override_settings
from channels.testing import WebsocketCommunicator

from websocket.consumers import CommentConsumer
from apps.comments.handlers import COMMENTS_GROUP


WS_URL = "/ws/comments/"

CHANNEL_LAYERS_OVERRIDE = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


def run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def make_app():
    """Create the ASGI application for testing.
    
    Converts the consumer class into an ASGI application using `as_asgi()` 
    that `WebsocketCommunicator` can talk to.
    This is what the test client expects.
    """
    return CommentConsumer.as_asgi()


class TestCommentConsumer:
    """
    A plain sync class. Every async test is defined as an inner
    `async def _test()` and called with `run(_test())` to avoid the need]
    the pytest-asyncio plugin and its event loop fixture.
    """

    @override_settings(CHANNEL_LAYERS = CHANNEL_LAYERS_OVERRIDE)
    def test_connect_accepted(self):
        """Test that a client can connect successfully.

        `communicator.connect()` sends the WebSocket handshake and returns `(connected: bool, subprotocol)`.
        Asserts `connected is True` - meaning `CommentConsumer.connect()` called `self.accept()`.
        If `accept()` were never called, the connection would be refused and `connected` would be `False`.

        `await communicator.disconnect()` is cleanup - important because an unclosed communicator
        can leave dangling state in the in-memory layer.
        """
        async def _test():
            communicator = WebsocketCommunicator(make_app(), WS_URL)  # Channels' built-in test client
            connected, _ = await communicator.connect()
            assert connected
            await communicator.disconnect()

        run(_test())

    @override_settings(CHANNEL_LAYERS = CHANNEL_LAYERS_OVERRIDE)
    def test_disconnect_does_not_raise(self):
        """Test that disconnecting does not raise an error."""
        async def _test():
            communicator = WebsocketCommunicator(make_app(), WS_URL)
            await communicator.connect()
            await communicator.disconnect()  # must not raise

        run(_test())

    @override_settings(CHANNEL_LAYERS = CHANNEL_LAYERS_OVERRIDE)
    def test_receive_from_client_ignored(self):
        """Test that sending a message from client does not cause an error."""
        async def _test():
            communicator = WebsocketCommunicator(make_app(), WS_URL)
            await communicator.connect()
            await communicator.send_to(text_data="anything")
            # server-push only: no response expected
            assert await communicator.receive_nothing()
            await communicator.disconnect()

        run(_test())

    @override_settings(CHANNEL_LAYERS = CHANNEL_LAYERS_OVERRIDE)
    def test_broadcast_event_forwarded_to_client(self):
        async def _test():
            """
            The core functional test: when a comment is created, the handler
            sends a message to the group, which should be received by the consumer and
            forwarded to the client.
            """
            from channels.layers import channel_layers
            channel_layers.backends = {}  # clear cached layer so override takes effect

            communicator = WebsocketCommunicator(make_app(), WS_URL)
            await communicator.connect()

            from channels.layers import get_channel_layer
            layer = get_channel_layer()
            await layer.group_send(
                COMMENTS_GROUP,
                {
                    "type": "comment.broadcast",
                    "id": "comment-uuid-1",
                    "text": "Hello",
                    "username": "alice",
                    "email": "alice@example.com",
                    "home_page": None,
                    "parent_id": None,
                    "created_at": "2024-01-01T00:00:00",
                }
            )

            response = await communicator.receive_json_from()
            assert response["id"] == "comment-uuid-1"
            assert response["text"] == "Hello"
            await communicator.disconnect()

        run(_test())

    @override_settings(CHANNEL_LAYERS = CHANNEL_LAYERS_OVERRIDE)
    def test_broadcast_strips_type_key(self):
        async def _test():
            from channels.layers import channel_layers
            channel_layers.backends = {}

            communicator = WebsocketCommunicator(make_app(), WS_URL)
            await communicator.connect()

            from channels.layers import get_channel_layer
            layer = get_channel_layer()
            await layer.group_send(
                COMMENTS_GROUP,
                {
                    "type": "comment.broadcast",
                    "id": "comment-uuid-2",
                    "text": "World",
                    "username": "bob",
                    "email": "bob@example.com",
                    "home_page": None,
                    "parent_id": None,
                    "created_at": "2024-01-01T00:00:00",
                }
            )

            response = await communicator.receive_json_from()
            assert "type" not in response

        run(_test())
