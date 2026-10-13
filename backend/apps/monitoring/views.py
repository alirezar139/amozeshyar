import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole

from .models import ErrorEvent, SupportReport
from .permissions import IsDeveloper
from .recorder import record, user_fields
from .serializers import ClientErrorSerializer, ErrorEventSerializer, ResolveReportSerializer, SupportReportSerializer

client_logger = logging.getLogger("live.client")

LIVE_BATCH = 200
REPORT_LOOKBACK = timedelta(hours=2)


class ClientErrorView(APIView):
    """Browser-side errors (JS, Vue, failed fetches). In production only signed-in users report,
    under the normal per-user throttle, so this can't be used to flood the log anonymously."""

    def get_authenticators(self):
        return [] if settings.DEBUG else super().get_authenticators()

    def get_permissions(self):
        return [permissions.AllowAny()] if settings.DEBUG else [permissions.IsAuthenticated()]

    def get_throttles(self):
        return [] if settings.DEBUG else super().get_throttles()

    def post(self, request):
        data = ClientErrorSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        client_logger.log(
            logging.WARNING if d["level"] == "warning" else logging.ERROR, "BROWSER %s on %s (%s): %s",
            d["kind"], d["url"], getattr(request.user, "email", None) or "anon", d["message"],
        )
        record(
            source="browser", level=d["level"], path=d["kind"], message=d["message"],
            detail=d.get("detail") or "", page_url=d["url"], **user_fields(request.user),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventListView(generics.ListAPIView):
    """Live feed for the developer: newest first, `?after=<id>` returns only what's new."""

    serializer_class = ErrorEventSerializer
    permission_classes = (IsDeveloper,)
    pagination_class = None

    def get_queryset(self):
        qs = ErrorEvent.objects.all()
        params = self.request.query_params
        if params.get("after", "").isdigit():
            qs = qs.filter(id__gt=int(params["after"]))
        if params.get("source") in ErrorEvent.Source.values:
            qs = qs.filter(source=params["source"])
        if params.get("level") in ErrorEvent.Level.values:
            qs = qs.filter(level=params["level"])
        return qs[:LIVE_BATCH]

    def delete(self, request):
        ErrorEvent.objects.filter(reports__isnull=True).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SupportReportViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """The developer's inbox of support reports; PATCH {"resolved": true} closes one."""

    serializer_class = SupportReportSerializer
    permission_classes = (IsDeveloper,)
    queryset = SupportReport.objects.prefetch_related("events")
    http_method_names = ("get", "patch")

    def get_serializer_class(self):
        return ResolveReportSerializer if self.action == "partial_update" else SupportReportSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("resolved") in ("true", "false"):
            qs = qs.filter(resolved=self.request.query_params["resolved"] == "true")
        return qs

    def perform_update(self, serializer):
        resolved = serializer.validated_data.get("resolved", serializer.instance.resolved)
        serializer.save(resolved_at=timezone.now() if resolved else None)


class SendSupportReportView(generics.CreateAPIView):
    """The instructor's "report a problem" button: their message plus their own recent errors."""

    serializer_class = SupportReportSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)

    def perform_create(self, serializer):
        user = self.request.user
        report = serializer.save(
            user=user, user_label=user.email, resolved=False,
            user_agent=self.request.META.get("HTTP_USER_AGENT", "")[:300],
        )
        recent = ErrorEvent.objects.filter(user=user, created_at__gte=timezone.now() - REPORT_LOOKBACK)[:50]
        report.events.set(recent)


class UnresolvedCountView(APIView):
    permission_classes = (IsDeveloper,)

    def get(self, request):
        return Response({"unresolved_reports": SupportReport.objects.filter(resolved=False).count()})
