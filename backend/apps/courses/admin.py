from django.contrib import admin

from .models import Category, Course, Lesson


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "status", "price", "created_at")
    list_filter = ("status", "level", "category")
    search_fields = ("title", "instructor__user__email")
    readonly_fields = ("slug",)
    inlines = (LessonInline,)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("course", "title", "order", "is_free_preview")
