from django.urls import path

from apps.captcha_app.views import CaptchaGenerateView

urlpatterns = [
    path("captcha/", CaptchaGenerateView.as_view(), name="captcha-generate"),
]
