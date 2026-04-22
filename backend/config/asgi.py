"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Initialize Django BEFORE importing anything that touches models
django_asgi_app = get_asgi_application()

from websocket.routing import websocket_urlpatterns  # noqa: E402 — must be after setup

application = ProtocolTypeRouter({
    # Standard HTTP requests go through Django as normal
    "http": django_asgi_app,
    
    # WebSocket requests get routed to our consumers
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
