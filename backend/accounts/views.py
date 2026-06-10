from rest_framework import generics
from .models import User, EmailOTP
from .serializers import RegisterSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenSerializer
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.utils.timezone import now
import random
from django.contrib.auth import get_user_model
import requests
from rest_framework import status
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

    def post(self, request):
        email = request.data.get("email")
        mode = request.data.get("mode")

        if not email or not mode:
            return Response({"error": "Email and mode required"}, status=400)

        email = email.lower().strip()

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
        otp = str(random.randint(100000, 999999))
        EmailOTP.objects.create(email=email, otp=otp)

        try:
            send_mail(
                "Your ParallaxLane OTP",
                f"Your OTP is {otp}. It expires in 5 minutes.",
                "no-reply@parallaxlane.com",
                [email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send OTP to {email}: {e}")
            return Response({"error": "Failed to send OTP. Please try again."}, status=500)

        return Response({"status": "OTP sent"})


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"error": "Email and OTP required"}, status=400)

        email = email.lower().strip()

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not registered"}, status=400)

        record = EmailOTP.objects.filter(email=email, otp=otp).last()
        if not record:
            return Response({"error": "Invalid OTP"}, status=400)

        if now() - record.created_at > timedelta(minutes=5):
            record.delete()  # FIX: clean up expired record
            return Response({"error": "OTP expired"}, status=400)

        refresh = RefreshToken.for_user(user)
        record.delete()

        org = getattr(user, "current_organisation", None)
        org_role = None
        if org:
            membership = org.members.filter(user=user, is_active=True).first()
            org_role = membership.role if membership else None

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "email": user.email,
            "display_name": user.name.split(" ")[0] if user.name else user.email.split("@")[0],
            "org_slug": org.slug if org else None,
            "org_role": org_role
        })


class VerifyOTPRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        name = request.data.get("name")
        password = request.data.get("password")

        if not all([email, otp, name, password]):
            return Response({"error": "All fields required"}, status=400)

        email = email.lower().strip()

        record = EmailOTP.objects.filter(email=email, otp=otp).last()
        if not record:
            return Response({"error": "Invalid OTP"}, status=400)

        if now() - record.created_at > timedelta(minutes=5):
            record.delete()  # FIX
            return Response({"error": "OTP expired"}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "User already exists"}, status=400)

        user = User.objects.create(email=email, username=email, name=name, role="candidate")
        user.set_password(password)
        user.save()
        record.delete()

        return Response({"message": "User registered successfully"})


class VerifyOTPForgotView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        new_password = request.data.get("password")

        if not email or not otp or not new_password:
            return Response({"error": "All fields required"}, status=400)

        email = email.lower().strip()

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not registered"}, status=400)

        record = EmailOTP.objects.filter(email=email, otp=otp).last()
        if not record:
            return Response({"error": "Invalid OTP"}, status=400)

        if now() - record.created_at > timedelta(minutes=5):
            record.delete()  # FIX
            return Response({"error": "OTP expired"}, status=400)

        user.set_password(new_password)
        user.save()
        record.delete()

        return Response({"message": "Password reset successful"})


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response({"error": "Token required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # FIX: added timeout=5 to prevent worker thread hang
            google_response = requests.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={token}",
                timeout=5
            )
        except requests.RequestException as e:
            logger.error(f"Google token verification error: {e}")
            return Response({"error": "Could not verify Google token"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if google_response.status_code != 200:
            return Response({"error": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST)

        data = google_response.json()
        email = data.get("email")
        full_name = data.get("name")
        given_name = data.get("given_name")
        picture = data.get("picture")

        if not email:
            return Response({"error": "Email not found in Google token"}, status=status.HTTP_400_BAD_REQUEST)

        display_name = given_name or full_name or ""

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "role": "candidate", "name": display_name}
        )

        if not user.name and display_name:
            user.name = display_name
            user.save()

        refresh = RefreshToken.for_user(user)

        response_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "email": user.email,
            "display_name": user.name.split(" ")[0] if user.name else user.email.split("@")[0],
            "picture": picture,
        }

        org = getattr(user, "current_organisation", None)
        if org:
            membership = org.members.filter(user=user, is_active=True).first()
            response_data.update({
                "org_slug": org.slug,
                "org_name": org.name,
                "org_plan": org.plan,
                "org_role": membership.role if membership else None
            })
        else:
            response_data["no_org"] = True

        return Response(response_data, status=status.HTTP_200_OK)