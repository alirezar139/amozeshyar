from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsAdminRole
from .serializers import EmailTokenObtainPairSerializer, RefreshResponseSerializer, RegisterSerializer, UserSerializer

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth/"


def _refresh_cookie_kwargs():
    lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    return {
        "max_age": int(lifetime.total_seconds()),
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": "Lax",
        "path": REFRESH_COOKIE_PATH,
    }


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)


class AdminCreateUserView(generics.CreateAPIView):
    """Admin-only: provision an instructor (or student) account directly.

    Reuses RegisterSerializer as-is — it already blocks self-selecting the
    admin role, and instructor accounts still get their InstructorProfile
    auto-created (pending_review) via the existing signal, so the admin can
    approve/edit it afterward like any other instructor profile.
    """

    serializer_class = RegisterSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)


class LoginView(TokenObtainPairView):
    """Issues an access token in the JSON body and the refresh token as an httpOnly cookie.

    Keeping the refresh token out of frontend-readable storage (localStorage)
    limits the blast radius of an XSS bug to the short-lived access token only.
    """

    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh = response.data.pop("refresh", None)
        if refresh:
            response.set_cookie(REFRESH_COOKIE_NAME, refresh, **_refresh_cookie_kwargs())
        return response


class RefreshView(APIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = RefreshResponseSerializer

    @extend_schema(responses=RefreshResponseSerializer)
    def post(self, request, *args, **kwargs):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw_refresh:
            return Response({"detail": "Refresh cookie missing."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            refresh = RefreshToken(raw_refresh)
            access = str(refresh.access_token)
        except TokenError:
            return Response({"detail": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        response = Response({"access": access})
        if settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"]:
            from apps.accounts.models import User

            user = User.objects.get(id=refresh["user_id"])
            refresh.blacklist()
            new_refresh = RefreshToken.for_user(user)
            response.set_cookie(REFRESH_COOKIE_NAME, str(new_refresh), **_refresh_cookie_kwargs())
        return response


class LogoutView(APIView):
    @extend_schema(request=None, responses={205: None})
    def post(self, request, *args, **kwargs):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_205_RESET_CONTENT)
        response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
        return response


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user
