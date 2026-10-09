from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("refresh/", views.RefreshView.as_view(), name="token-refresh"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", views.ResendVerificationView.as_view(), name="resend-verification"),
    path("reset-password/", views.PasswordResetRequestView.as_view(), name="reset-password"),
    path("reset-password/confirm/", views.PasswordResetConfirmView.as_view(), name="reset-password-confirm"),
    path("me/", views.MeView.as_view(), name="me"),
]
