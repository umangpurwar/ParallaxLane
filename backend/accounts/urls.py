from django.urls import path
from .views import (
    RegisterView, SendOTPView, VerifyOTPView,
    VerifyOTPRegisterView, VerifyOTPForgotView, LogoutView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("send-otp/", SendOTPView.as_view()),
    path("verify-otp/", VerifyOTPView.as_view()),
    path("verify-otp-register/", VerifyOTPRegisterView.as_view()),
    path("verify-otp-forgot/", VerifyOTPForgotView.as_view()),
    path("logout/", LogoutView.as_view()),
]
