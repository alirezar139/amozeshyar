from django.contrib import admin

from .models import InstructorProfile


@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "slug", "is_site_owner", "rating_avg", "total_students", "created_at")
    search_fields = ("user__email", "slug", "headline")
    readonly_fields = ("slug", "rating_avg", "total_students", "created_at", "updated_at")
