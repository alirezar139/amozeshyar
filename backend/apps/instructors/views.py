from django.http import Http404
from rest_framework import generics, permissions

from apps.accounts.permissions import IsAdminRole

from .serializers import PublicInstructorSerializer, SiteSettingsSerializer
from .site import get_site_owner


def _site_owner_or_404():
    owner = get_site_owner()
    if owner is None:
        raise Http404("Site owner not set up yet — run `manage.py setup_site`.")
    return owner


class SiteOwnerView(generics.RetrieveAPIView):
    """Public: who this site belongs to — drives the homepage hero and SEO."""

    serializer_class = PublicInstructorSerializer
    permission_classes = (permissions.AllowAny,)

    def get_object(self):
        return _site_owner_or_404()


class SiteSettingsView(generics.RetrieveUpdateAPIView):
    """Admin (the instructor themself): edit the public profile shown on the site."""

    serializer_class = SiteSettingsSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        return _site_owner_or_404()
