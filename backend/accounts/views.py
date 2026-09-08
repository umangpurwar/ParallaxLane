from rest_framework import generics
from .models import User, EmailOTP
from .serializers import RegisterSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenSerializer
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.http import JsonResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from datetime import timedelta
from django.utils.timezone import now
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db import connection
from django.db.utils import DatabaseError
from django.views.decorators.http import require_GET
from organisations.utils import sync_user_organisation_context
from .otp_security import check_verify_allowed, record_failed_verify, clear_verify_attempts
from .ratelimit_keys import post_email_key
from core.validators import normalize_email
from core.email_service import EmailDeliveryError
from .otp_service import issue_otp
User = get_user_model()


def _revoke_refresh_tokens(user):
    """Blacklist every outstanding refresh token for a user."""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='3/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code != 201:
            return response

        try:
            issue_otp(
                email=response.data["email"],
                purpose="account_verification",
            )
        except EmailDeliveryError:
            User.objects.filter(pk=response.data["id"]).delete()
            return Response(
                {"error": "Failed to send verification email. Please try again."},
                status=503,
            )
        return response


class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@require_GET
def health_check(request):
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse(
            {"status": "unhealthy", "database": "unavailable"},
            status=503,
        )

    return JsonResponse({"status": "ok", "database": "ok"})


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

        user = User.objects.filter(email__iexact=email).first()
        if mode == "register" and user and user.is_active:
            return Response({"status": "If eligible, an OTP was sent"})
        if mode in ["login", "forgot"] and (not user or not user.is_active):
            return Response({"status": "If eligible, an OTP was sent"})

        try:
            issue_otp(
                email=email,
                purpose="password_reset" if mode == "forgot" else "account_verification",
            )
        except EmailDeliveryError:
            return Response({"error": "Failed to send OTP. Please try again."}, status=503)

        # OTP is never returned in API responses (see C-004).
        return Response({"status": "If eligible, an OTP was sent"})


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

        records = EmailOTP.objects.filter(email=email).order_by("-created_at")[:5]
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

        if not user.is_active:
            return Response({"error": "Account is inactive"}, status=403)

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

        records = EmailOTP.objects.filter(email=email).order_by("-created_at")[:5]
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
            validate_password(password)
        except ValidationError as e:
            return Response({"error": "\n".join(e.messages)}, status=400)

        user = User.objects.filter(email__iexact=email).first()
        if user and user.is_active:
            return Response({"error": "User already exists"}, status=400)
        if user is None:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                name=name,
                role="candidate",
                is_active=False,
            )
        else:
            user.set_password(password)
            user.name = name
            user.is_active = False
            user.save(update_fields=["password", "name", "is_active"])

        user.is_active = True
        user.save(update_fields=["is_active"])
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

        records = EmailOTP.objects.filter(email=email).order_by("-created_at")[:5]
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

        if not user.is_active:
            return Response({"error": "Account is inactive"}, status=403)

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({"error": "\n".join(e.messages)}, status=400)

        with transaction.atomic():
            user.set_password(new_password)
            user.save(update_fields=["password"])
            record.delete()
            _revoke_refresh_tokens(user)
        clear_verify_attempts(email)

        return Response({"message": "Password reset successful"})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                if str(token.get("user_id")) != str(request.user.pk):
                    return Response({"error": "Refresh token does not belong to this user"}, status=403)
                token.blacklist()
            except Exception:
                return Response({"error": "Invalid refresh token"}, status=400)
        return Response({"status": "logged out"})
