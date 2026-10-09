"""
Serializers translate between Python objects (model instances) and JSON,
and they VALIDATE incoming data. Think of them as "forms" for an API.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .services import get_user_from_uid_and_token, send_verification_email

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    # write_only = accepted on input, never shown in responses
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, label="Confirm password")

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name",
                  "phone_number", "password", "password2"]

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        validate_password(attrs["password"])  # Django's built-in strength rules
        return attrs

    def create(self, validated_data):
        # create_user() HASHES the password (never store plain text!)
        user = User.objects.create_user(role=User.Role.USER, **validated_data)
        send_verification_email(user)
        return user


class LoginSerializer(TokenObtainPairSerializer):
    """SimpleJWT's login serializer + role info + optional email-verified check."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role  # stored inside the JWT itself
        token["email"] = user.email
        return token

    def validate(self, attrs):
        attrs[self.username_field] = attrs[self.username_field].lower()
        data = super().validate(attrs)  # checks email + password, makes tokens
        user = self.user
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_email_verified and not user.is_admin_role:
            raise AuthenticationFailed("Please verify your email address before logging in.")
        data["user"] = {"id": user.id, "email": user.email, "role": user.role}
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def save(self, **kwargs):
        try:
            RefreshToken(self.validated_data["refresh"]).blacklist()
        except TokenError:
            raise serializers.ValidationError({"refresh": "Token is invalid or already used."})


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        user = get_user_from_uid_and_token(attrs["uid"], attrs["token"])
        if user is None:
            raise serializers.ValidationError("Invalid or expired verification link.")
        attrs["user"] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = get_user_from_uid_and_token(attrs["uid"], attrs["token"])
        if user is None:
            raise serializers.ValidationError("Invalid or expired reset link.")
        validate_password(attrs["new_password"], user)
        attrs["user"] = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    """The logged-in user's own profile (GET/PATCH /api/auth/me/)."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name",
                  "phone_number", "role", "is_email_verified", "date_joined"]
        read_only_fields = ["id", "email", "role", "is_email_verified", "date_joined"]


class AdminUserSerializer(serializers.ModelSerializer):
    """Admins may change a user's role or suspend (is_active=False) them."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "phone_number",
                  "role", "is_active", "is_email_verified", "date_joined"]
        read_only_fields = ["id", "email", "date_joined"]
