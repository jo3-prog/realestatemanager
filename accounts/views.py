from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .permissions import IsAdminRole
from .serializers import (
    AdminUserSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    RegisterSerializer,
    VerifyEmailSerializer,
)
from .services import send_password_reset_email, send_verification_email

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ : create a normal user account."""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth"  # rate limit: see settings


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ : email + password -> access & refresh tokens."""
    serializer_class = LoginSerializer
    throttle_scope = "auth"


class RefreshView(TokenRefreshView):
    """POST /api/auth/refresh/ : trade a refresh token for a new access token."""
    throttle_scope = "auth"


class LogoutView(generics.GenericAPIView):
    """POST /api/auth/logout/ : blacklist the refresh token so it cannot be reused."""
    serializer_class = LogoutSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)


class VerifyEmailView(generics.GenericAPIView):
    """GET (from the emailed link) or POST /api/auth/verify-email/ ."""
    serializer_class = VerifyEmailSerializer
    permission_classes = [AllowAny]

    def _verify(self, data):
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        return Response({"detail": "Email verified. You can now log in."})

    def get(self, request):
        return self._verify(request.query_params)

    def post(self, request):
        return self._verify(request.data)


class ResendVerificationView(APIView):
    """POST /api/auth/resend-verification/ (logged in)."""
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth"

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        if request.user.is_email_verified:
            return Response({"detail": "Email already verified."})
        send_verification_email(request.user)
        return Response({"detail": "Verification email sent."})


class PasswordResetRequestView(generics.GenericAPIView):
    """POST /api/auth/reset-password/ : email a reset link/token."""
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user:
            send_password_reset_email(user)
        # Same answer whether or not the email exists (don't leak who is registered).
        return Response({"detail": "If that email exists, a reset message has been sent."})


class PasswordResetConfirmView(generics.GenericAPIView):
    """POST /api/auth/reset-password/confirm/ : set the new password."""
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "Password has been reset."})


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ : the logged-in user's own profile."""
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


class AdminUserViewSet(viewsets.ModelViewSet):
    """/api/admin/users/ : admins manage all users (list, edit role, suspend, delete)."""
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "username", "first_name", "last_name"]
