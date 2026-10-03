from django.contrib import admin

from .models import Attempt, Exam, Question


class QuestionInline(admin.TabularInline):
    model = Question
    fields = ("order", "kind", "text", "points", "time_limit_seconds")
    extra = 0


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "status", "duration_minutes", "available_until")
    list_filter = ("status", "course")
    inlines = (QuestionInline,)


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("exam", "student", "status", "score", "max_score", "submitted_at")
    list_filter = ("status", "exam")
