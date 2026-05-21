import json
import logging
from typing import Optional

from channels.generic.websocket import AsyncWebsocketConsumer

from apps.comments.handlers import COMMENTS_GROUP

log = logging.getLogger(__name__)


class CommentConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time comment updates.

    Connection lifecycle:
        connect()    → join the comments group
        disconnect() → leave the group
        receive()    → not used (read-only push from server)
        comment.broadcast → called by channel layer when group_send fires

    All connected clients receive every new comment instantly.
    """

    async def connect(self) -> None:
        """Accept connection and join the shared comments group."""
        await self.channel_layer.group_add(
            COMMENTS_GROUP,
            self.channel_name,
        )
        await self.accept()
        log.debug(f"WS connected: channel={self.channel_name}")

    async def disconnect(self, close_code: int) -> None:
        """Leave the group on disconnect - no cleanup needed."""
        await self.channel_layer.group_discard(
            COMMENTS_GROUP,
            self.channel_name,
        )
        log.debug(
            f"WS disconnected: channel={self.channel_name} code={close_code}"
        )

    async def receive(
        self, text_data: Optional[str] = None, bytes_data=None
    ) -> None:
        """Client → server messages are ignored.

        This is a server-push only channel.
        Clients connect to listen, not to send.
        """
        pass

    async def comment_broadcast(self, event: dict) -> None:
        """Receive a message from the channel layer group & forward to client.

        This method name maps to the `type` field in `group_send` payload.

        :param event: The payload dict sent by `on_comment_created` handler.
        :return: `None`. Sends JSON to client but does not return data to caller.
        """
        payload = {k: v for k, v in event.items() if k != "type"}

        await self.send(text_data=json.dumps(payload))
        log.debug(f"Pushed comment {payload.get('id')} to {self.channel_name}")
