from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsVideoOwnerOrAdmin(BasePermission):
    """Only the owning instructor or an admin may access the original-file download endpoint."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.ADMIN:
            return True
        return obj.lesson.course.instructor.user_id == request.user.id
