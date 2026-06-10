from django.urls import path
from .views import RegisterView, SendOTPView, VerifyOTPView, GoogleAuthView,VerifyOTPRegisterView,VerifyOTPForgotView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("send-otp/", SendOTPView.as_view()),
    path("verify-otp/", VerifyOTPView.as_view()),
    path("google/", GoogleAuthView.as_view()),
    path("verify-otp-register/", VerifyOTPRegisterView.as_view()),
    path("verify-otp-forgot/", VerifyOTPForgotView.as_view())

]