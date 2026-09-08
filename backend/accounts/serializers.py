from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from core.validators import normalize_email
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from organisations.utils import sync_user_organisation_context

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "password", "name"]

    def validate_email(self, value):
        value = normalize_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]
        name = validated_data.get("name", "")

        # Create user using email as username internally
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
        )

        # Set additional fields
        user.name = name
        user.role = "candidate"
        user.is_active = False
        user.save()

        return user

class CustomTokenSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError("Email and password required")

        user = User.objects.filter(email__iexact=email).first()
        if user and not user.is_active:
            raise serializers.ValidationError("Account is inactive")

        # Authenticate using Django auth system
        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials")

        # Generate tokens manually
        refresh = RefreshToken.for_user(user)

        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "email": user.email,
            "display_name": (user.name.split(" ")[0] if user.name else user.email.split("@")[0]),
        }

        org_data = sync_user_organisation_context(user)
        data.update({
            "org_slug": org_data.get("org_slug"),
            "org_name": org_data.get("org_name"),
            "org_plan": org_data.get("org_plan"),
            "org_role": org_data.get("org_role"),
        })

        return data
