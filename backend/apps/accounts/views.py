from django.conf import settings
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsAdminRole
from .serializers import (
    AdminUserSerializer,
    EmailTokenObtainPairSerializer,
    RefreshResponseSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()

REFRESH_COOKIE_NAME = "refresh_token"
# Must be "/" (not scoped to /api/v1/auth/): the Nuxt frontend forwards
# this cookie by hand on every SSR request (see frontend/composables/useApi.ts)
# so a page like /courses/<slug> can render the visitor's real is_enrolled/
# progress state on first load — a narrower path means the browser never
# even includes the cookie in the request the frontend server sees.
REFRESH_COOKIE_PATH = "/"


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


class AdminUserViewSet(viewsets.ModelViewSet):
    """Admin's user directory: search everyone, change a role, activate/deactivate.

    Read/patch only (no delete, no create — creation goes through
    AdminCreateUserView) and an admin can never edit their own row through
    here, so this endpoint can't be used to accidentally strip your own
    admin role or deactivate yourself out of the panel.
    """

    serializer_class = AdminUserSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    http_method_names = ("get", "patch", "head", "options")
    filter_backends = (filters.SearchFilter,)
    search_fields = ("email", "first_name", "last_name")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        return User.objects.all().order_by("-date_joined")

    def perform_update(self, serializer):
        if serializer.instance.id == self.request.user.id:
            raise PermissionDenied("Cannot change your own role or active status here.")
        serializer.save()


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
