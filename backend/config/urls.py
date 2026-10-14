"""Root URL configuration. All API endpoints are namespaced under /api/v1/."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.common.views import HealthView

api_v1_patterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/", include("apps.accounts.urls")),
    path("site/", include("apps.instructors.urls")),
    path("", include("apps.courses.urls")),
    path("", include("apps.videos.urls")),
    path("", include("apps.enrollments.urls")),
    path("payments/", include("apps.payments.urls")),
    path("", include("apps.messaging.urls")),
    path("", include("apps.board.urls")),
    path("", include("apps.exams.urls")),
    path("", include("apps.monitoring.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1_patterns)),
    # API documentation (drf-spectacular). Public in dev; staff-only in production
    # (SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"] in settings/prod.py).
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
