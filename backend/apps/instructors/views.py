from django.http import Http404
from rest_framework import generics, permissions

from apps.accounts.permissions import IsAdminRole
from apps.common import public_cache

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

    def retrieve(self, request, *args, **kwargs):
        # The same for every visitor and fetched on every page (header, footer, hero).
        return public_cache.cached_response(request, lambda: super(SiteOwnerView, self).retrieve(request, *args, **kwargs).data)


class SiteSettingsView(generics.RetrieveUpdateAPIView):
    """Admin (the instructor themself): edit the public profile shown on the site."""

    serializer_class = SiteSettingsSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        return _site_owner_or_404()
