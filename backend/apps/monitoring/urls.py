from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("monitoring/reports", views.SupportReportViewSet, basename="support-report")

urlpatterns = [
    path("monitoring/client-log/", views.ClientErrorView.as_view(), name="monitoring-client-log"),
    path("monitoring/events/", views.EventListView.as_view(), name="monitoring-events"),
    path("monitoring/summary/", views.UnresolvedCountView.as_view(), name="monitoring-summary"),
    path("support/reports/", views.SendSupportReportView.as_view(), name="support-report-create"),
    *router.urls,
]
