from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from . import captcha
from .permissions import IsAdminRole
from .serializers import (
    AdminUserSerializer,
    CaptchaChallengeSerializer,
    CaptchaNumberChallengeSerializer,
    CaptchaPassSerializer,
    CaptchaVerifyNumberRequestSerializer,
    CaptchaVerifyRequestSerializer,
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
    """Also logs the new account straight in (same token/cookie shape as
    LoginView) so the frontend doesn't need a second round-trip.

    Deliberately does NOT require the captcha — that gate is specifically
    for the login *form*, where credential-stuffing bots would otherwise
    hammer known email/password pairs; a fresh registration doesn't have
    that risk profile the same way.
    """

    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AnonRateThrottle, ScopedRateThrottle)
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        response = Response(
            {"access": str(refresh.access_token), **serializer.data},
            status=status.HTTP_201_CREATED,
        )
        response.set_cookie(REFRESH_COOKIE_NAME, str(refresh), **_refresh_cookie_kwargs())
        return response


class AdminUserViewSet(viewsets.ModelViewSet):
    """Admin's user directory: search everyone, change a role, activate/deactivate.

    Read/patch only (no delete, no create — students sign up themselves)
    and an admin can never edit their own row through
    here, so this endpoint can't be used to accidentally strip your own
    admin role or deactivate yourself out of the panel.

    Developer accounts (superusers, see `setup_site`) are invisible and
    untouchable here unless the requester is a developer too, so the
    instructor running the site can't lock the developer out.
    """

    serializer_class = AdminUserSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    http_method_names = ("get", "patch", "post", "head", "options")
    filter_backends = (filters.SearchFilter,)
    search_fields = ("email", "first_name", "last_name")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        users = User.objects.all().order_by("-date_joined")
        if not self.request.user.is_superuser:
            users = users.exclude(is_superuser=True)
        return users

    def perform_update(self, serializer):
        if serializer.instance.id == self.request.user.id:
            raise PermissionDenied("نقش یا وضعیت فعال بودن حساب خودتان را از اینجا نمی‌توانید تغییر دهید.")
        serializer.save()

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")  # POST is only for set-password; users sign up themselves

    @action(detail=True, methods=["get", "post"])
    def courses(self, request, pk=None):
        """A student's courses, for enrolling by hand (e.g. paid in person).

        GET: every course with `enrolled`. POST {"course": id, "enrolled": bool}
        enrolls (or re-activates) / deactivates — no payment involved.
        """
        from apps.courses.models import Course
        from apps.enrollments.models import Enrollment

        user = self.get_object()
        if user.role != User.Role.STUDENT:
            raise ValidationError("فقط دانشجو را می‌توان در دوره ثبت‌نام کرد.")
        if request.method == "POST":
            course = Course.objects.filter(pk=request.data.get("course")).first()
            if course is None:
                raise ValidationError({"course": "دوره پیدا نشد."})
            if request.data.get("enrolled"):
                enrollment, created = Enrollment.objects.get_or_create(student=user, course=course)
                if not created and not enrollment.is_active:
                    enrollment.is_active = True
                    enrollment.save(update_fields=["is_active", "updated_at"])
            else:
                Enrollment.objects.filter(student=user, course=course).update(is_active=False)
        active = set(Enrollment.objects.filter(student=user, is_active=True).values_list("course_id", flat=True))
        return Response([
            {"id": c.id, "title": c.title, "status": c.status, "enrolled": c.id in active}
            for c in Course.objects.order_by("title")
        ])

    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        """Body {"password": "..."}: set a new password (the old one can't be
        shown — only its hash is stored). Signs the user out of their other
        sessions, unless it's the admin's own account."""
        user = self.get_object()
        password = request.data.get("password") or ""
        try:
            validate_password(password, user)
        except DjangoValidationError as e:
            raise ValidationError({"password": list(e.messages)}) from None
        user.set_password(password)
        user.save(update_fields=["password"])
        if user.id != request.user.id:
            BlacklistedToken.objects.bulk_create(
                [BlacklistedToken(token=t) for t in OutstandingToken.objects.filter(user=user)], ignore_conflicts=True
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginView(TokenObtainPairView):
    """Issues an access token in the JSON body and the refresh token as an httpOnly cookie.

    Keeping the refresh token out of frontend-readable storage (localStorage)
    limits the blast radius of an XSS bug to the short-lived access token only.
    """

    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = (permissions.AllowAny,)
    # Per-IP cap on password guesses, on top of the captcha.
    throttle_classes = (AnonRateThrottle, ScopedRateThrottle)
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        if not captcha.consume_pass(request.data.get("captcha_pass_token")):
            return Response({"detail": "لطفاً پازل امنیتی را کامل کنید."}, status=status.HTTP_400_BAD_REQUEST)
        response = super().post(request, *args, **kwargs)
        refresh = response.data.pop("refresh", None)
        if refresh:
            response.set_cookie(REFRESH_COOKIE_NAME, refresh, **_refresh_cookie_kwargs())
        return response


class CaptchaChallengeView(APIView):
    """Public: hands out a fresh drag-the-gem puzzle. Not rate-limited beyond
    the shared `anon` throttle — each challenge is single-use and expires in
    2 minutes either way, so there's no benefit to requesting many at once."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = CaptchaChallengeSerializer

    @extend_schema(responses=CaptchaChallengeSerializer)
    def get(self, request):
        return Response(captcha.generate_challenge())


class CaptchaVerifyView(APIView):
    """Public: checks a drag attempt against the secret target (stage 1 of
    2) and, on success, hands back stage 2 — a distorted code to type in.
    Passing this alone does not unlock login."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = CaptchaNumberChallengeSerializer

    @extend_schema(request=CaptchaVerifyRequestSerializer, responses=CaptchaNumberChallengeSerializer)
    def post(self, request):
        stage2 = captcha.verify_puzzle(request.data.get("token"), request.data.get("x"))
        if not stage2:
            return Response({"detail": "جای‌گذاری درست نبود، دوباره تلاش کنید."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(stage2)


class CaptchaVerifyNumberView(APIView):
    """Public: checks stage 2's typed code and, only on success, issues the
    short-lived one-time pass that LoginView requires."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = CaptchaPassSerializer

    @extend_schema(request=CaptchaVerifyNumberRequestSerializer, responses=CaptchaPassSerializer)
    def post(self, request):
        pass_token = captcha.verify_number_and_issue_pass(request.data.get("token"), request.data.get("code"))
        if not pass_token:
            return Response({"detail": "کد وارد شده درست نیست، دوباره تلاش کنید."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"pass_token": pass_token})


class RefreshView(APIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = RefreshResponseSerializer

    @extend_schema(responses=RefreshResponseSerializer)
    def post(self, request, *args, **kwargs):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw_refresh:
            return Response({"detail": "نشست شما پیدا نشد؛ دوباره وارد شوید."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            refresh = RefreshToken(raw_refresh)
        except TokenError:
            # Leave the cookie alone: this is usually an already-rotated token from a
            # refresh that raced another one, and the browser may by now hold the newer,
            # valid cookie that the winner set. Clearing it here would log the user out.
            return self._expired()

        # A token outlives the account it was issued for: a deactivated or deleted
        # user must not keep minting access tokens until the cookie expires.
        user = get_user_model().objects.filter(id=refresh["user_id"], is_active=True).first()
        if user is None:
            refresh.blacklist()
            response = self._expired()
            response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
            return response

        response = Response({"access": str(refresh.access_token)})
        if settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"]:
            refresh.blacklist()
            new_refresh = RefreshToken.for_user(user)
            response.set_cookie(REFRESH_COOKIE_NAME, str(new_refresh), **_refresh_cookie_kwargs())
        return response

    @staticmethod
    def _expired():
        return Response({"detail": "نشست شما منقضی شده؛ دوباره وارد شوید."}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """Revokes the refresh cookie the request carries and clears it.

    Open to anonymous requests: it only acts on the caller's own cookie, and
    logging out must still work after the 15-minute access token has expired.
    """

    permission_classes = (permissions.AllowAny,)

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
