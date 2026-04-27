from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.captcha_app.services import CaptchaService


class CaptchaGenerateView(APIView):
    """GET /api/captcha/ — returns a fresh CAPTCHA token + image.

    The image is a base64-encoded PNG.

    The token must be submitted with the comment form as `captcha_token`.
    """

    def get(self, request: Request) -> Response:
        service = CaptchaService()
        data = service.generate()
        return Response(data)
