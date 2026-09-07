from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("admin/users", views.AdminUserViewSet, basename="admin-user")

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("admin/create-user/", views.AdminCreateUserView.as_view(), name="admin-create-user"),
    path("captcha/challenge/", views.CaptchaChallengeView.as_view(), name="captcha-challenge"),
    path("captcha/verify/", views.CaptchaVerifyView.as_view(), name="captcha-verify"),
    path("captcha/verify-number/", views.CaptchaVerifyNumberView.as_view(), name="captcha-verify-number"),
] + router.urls
