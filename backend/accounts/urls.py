from django.urls import path
from .views import (
    RegisterView, SendOTPView, VerifyOTPView,
    VerifyOTPRegisterView, VerifyOTPForgotView, LogoutView,
)
from .device_views import MyDevicesView, RegisterDeviceView
from .me_views import MeView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("send-otp/", SendOTPView.as_view()),
    path("verify-otp/", VerifyOTPView.as_view()),
    path("verify-otp-register/", VerifyOTPRegisterView.as_view()),
    path("verify-otp-forgot/", VerifyOTPForgotView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("devices/register/", RegisterDeviceView.as_view()),
    path("devices/me/", MyDevicesView.as_view()),
    path("me/", MeView.as_view()),
]
