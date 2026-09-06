from django.contrib import admin

from .models import Enrollment, WishlistItem


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "is_active", "access_granted_at")
    list_filter = ("is_active",)
    search_fields = ("student__email", "course__title")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "created_at")
