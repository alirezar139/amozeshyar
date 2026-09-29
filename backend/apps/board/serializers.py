from django.db.models import Max
from rest_framework import serializers

from .models import BoardCard


class BoardCardSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True, default=None)

    class Meta:
        model = BoardCard
        fields = (
            "id", "title", "description", "column", "position", "color", "due_date",
            "course", "course_title", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {"position": {"required": False}}

    def create(self, validated_data):
        if "position" not in validated_data:
            # New cards go to the bottom of their column.
            last = BoardCard.objects.filter(column=validated_data.get("column", BoardCard.Column.IDEA)).aggregate(m=Max("position"))["m"]
            validated_data["position"] = (last or 0) + 1024
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
