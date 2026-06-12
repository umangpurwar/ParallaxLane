from rest_framework import generics
from .models import User, EmailOTP
from .serializers import RegisterSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenSerializer
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.http import JsonResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.utils.timezone import now
import secrets
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from rest_framework import status
from django.conf import settings
from organisations.utils import sync_user_organisation_context
from .google_auth import verify_google_id_token
from .otp_security import check_verify_allowed, record_failed_verify, clear_verify_attempts
from .ratelimit_keys import post_email_key
from core.validators import normalize_email
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='3/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


def health_check(request):
    return JsonResponse({"status": "ok"})


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    @method_decorator(ratelimit(key=post_email_key, rate='3/m', method='POST', block=True))
    def post(self, request):
        email = request.data.get("email")
        mode = request.data.get("mode")

        if not email or not mode:
            return Response({"error": "Email and mode required"}, status=400)

        try:
            email = normalize_email(email)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)

        if mode not in ["login", "register", "forgot"]:
            return Response({"error": "Invalid mode"}, status=400)

        user_exists = User.objects.filter(email=email).exists()

        if mode == "login" and not user_exists:
            return Response({"error": "User not registered"}, status=400)
        if mode == "register" and user_exists:
            return Response({"error": "User already exists"}, status=400)
        if mode == "forgot" and not user_exists:
            return Response({"error": "User not registered"}, status=400)

        EmailOTP.objects.filter(email=email).delete()
        otp = str(secrets.randbelow(900000) + 100000)  # 6-digit OTP, cryptographically secure
        otp_record = EmailOTP(email=email)
        otp_record.set_otp(otp)
        otp_record.save()

        try:
            send_mail(
                "Your ParallaxLane OTP",
                f"Your OTP is {otp}. It expires in 5 minutes.",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error("Failed to send OTP to %s: %s", email, e)
            if settings.DEBUG:
                logger.warning("DEBUG mode: OTP email delivery failed for %s", email)
            else:
                return Response({"error": "Failed to send OTP. Please try again."}, status=500)

        # OTP is never returned in API responses (see C-004).
        return Response({"status": "OTP sent"})


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='15/m', method='POST', block=True))
    @method_decorator(ratelimit(key=post_email_key, rate='5/m', method='POST', block=True))
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"error": "Email and OTP required"}, status=400)

        email = email.lower().strip()

        allowed, message = check_verify_allowed(email)
        if not allowed:
            return Response({"error": message}, status=429)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not registered"}, status=400)

        records = EmailOTP.objects.filter(email=email).order_by("-created_at")
        record = None
        for r in records:
            if r.check_otp(otp):
                record = r
                break
        if not record:
            record_failed_verify(email)
            return Response({"error": "Invalid OTP"}, status=400)

        if now() - record.created_at > timedelta(minutes=5):
            record.delete()
            record_failed_verify(email)
            return Response({"error": "OTP expired"}, status=400)

        refresh = RefreshToken.for_user(user)
        record.delete()
        clear_verify_attempts(email)

        org_data = sync_user_organisation_context(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "email": user.email,
            "display_name": user.name.split(" ")[0] if user.name else user.email.split("@")[0],
            "org_slug": org_data.get("org_slug"),
            "org_name": org_data.get("org_name"),
            "org_plan": org_data.get("org_plan"),
            "org_role": org_data.get("org_role"),
        })


class VerifyOTPRegisterView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='15/m', method='POST', block=True))
    @method_decorator(ratelimit(key=post_email_key, rate='5/m', method='POST', block=True))
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        name = request.data.get("name")
        password = request.data.get("password")

        if not all([email, otp, name, password]):
            return Response({"error": "All fields required"}, status=400)

        email = email.lower().strip()

        allowed, message = check_verify_allowed(email)
        if not allowed:
            return Response({"error": message}, status=429)

        records = EmailOTP.objects.filter(email=email).order_by("-created_at")
        record = None
        for r in records:
            if r.check_otp(otp):
                record = r
                break
        if not record:
            record_failed_verify(email)
            return Response({"error": "Invalid OTP"}, status=400)

        if now() - record.created_at > timedelta(minutes=5):
            record.delete()
            record_failed_verify(email)
            return Response({"error": "OTP expired"}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "User already exists"}, status=400)

        try:
            validate_password(password)
        except ValidationError as e:
            return Response({"error": "\n".join(e.messages)}, status=400)

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            name=name,
            role="candidate",
        )
        record.delete()
        clear_verify_attempts(email)

        org_data = sync_user_organisation_context(user)
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "User registered successfully",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "email": user.email,
            "display_name": user.name.split(" ")[0] if user.name else user.email.split("@")[0],
            "org_slug": org_data.get("org_slug"),
            "org_name": org_data.get("org_name"),
            "org_plan": org_data.get("org_plan"),
            "org_role": org_data.get("org_role"),
        })


class VerifyOTPForgotView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='15/m', method='POST', block=True))
    @method_decorator(ratelimit(key=post_email_key, rate='5/m', method='POST', block=True))
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        new_password = request.data.get("password")

        if not email or not otp or not new_password:
            return Response({"error": "All fields required"}, status=400)

        email = email.lower().strip()

        allowed, message = check_verify_allowed(email)
        if not allowed:
            return Response({"error": message}, status=429)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not registered"}, status=400)

        records = EmailOTP.objects.filter(email=email).order_by("-created_at")
        record = None
        for r in records:
            if r.check_otp(otp):
                record = r
                break
        if not record:
            record_failed_verify(email)
            return Response({"error": "Invalid OTP"}, status=400)

        if now() - record.created_at > timedelta(minutes=5):
            record.delete()
            record_failed_verify(email)
            return Response({"error": "OTP expired"}, status=400)

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({"error": "\n".join(e.messages)}, status=400)
        user.set_password(new_password)
        user.save()
        record.delete()
        clear_verify_attempts(email)

        return Response({"message": "Password reset successful"})


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True))
    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response({"error": "Token required"}, status=status.HTTP_400_BAD_REQUEST)

        if not getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", ""):
            return Response(
                {"error": "Google OAuth is not configured on the server"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            data = verify_google_id_token(token)
        except ValueError as e:
            logger.warning("Google token validation failed: %s", e)
            message = str(e)
            if "not configured" in message.lower():
                return Response(
                    {"error": message},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            if "too early" in message.lower() or "expired" in message.lower():
                return Response(
                    {"error": "Google token expired or clock skew detected. Try again."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if "email is not verified" in message.lower():
                return Response(
                    {"error": "Google account email is not verified."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response({"error": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Google token verification error: %s", e)
            err = str(e).lower()
            if "audience" in err or "recipient" in err:
                return Response(
                    {"error": "Google OAuth client ID mismatch between frontend and backend."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"error": "Could not verify Google token"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        email = data.get("email")
        full_name = data.get("name")
        given_name = data.get("given_name")
        picture = data.get("picture")

        display_name = given_name or full_name or ""

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "role": "candidate", "name": display_name}
        )

        if not user.name and display_name:
            user.name = display_name
            user.save()

        refresh = RefreshToken.for_user(user)

        org_data = sync_user_organisation_context(user)
        response_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "email": user.email,
            "display_name": user.name.split(" ")[0] if user.name else user.email.split("@")[0],
            "picture": picture,
            "org_slug": org_data.get("org_slug"),
            "org_name": org_data.get("org_name"),
            "org_plan": org_data.get("org_plan"),
            "org_role": org_data.get("org_role"),
        }
        if not org_data:
            response_data["no_org"] = True

        return Response(response_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                logger.warning("Failed to blacklist refresh token on logout")
        return Response({"status": "logged out"})
