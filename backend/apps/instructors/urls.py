from django.urls import path

from . import views

urlpatterns = [
    path("", views.SiteOwnerView.as_view(), name="site-owner"),
    path("settings/", views.SiteSettingsView.as_view(), name="site-settings"),
]
