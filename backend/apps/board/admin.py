from django.contrib import admin

from .models import BoardCard


@admin.register(BoardCard)
class BoardCardAdmin(admin.ModelAdmin):
    list_display = ("title", "column", "color", "due_date", "course")
    list_filter = ("column",)
