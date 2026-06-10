from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "password", "name"]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
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

        # Organisation logic
        org = getattr(user, "current_organisation", None)

        if org:
            membership = org.members.filter(user=user, is_active=True).first()
            data.update({
                "org_slug": org.slug,
                "org_name": org.name,
                "org_plan": org.plan,
                "org_role": membership.role if membership else None
            })
        else:
            data.update({
                "org_slug": None,
                "org_name": None,
                "org_plan": None,
                "org_role": None
            })

        return data