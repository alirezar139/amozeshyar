from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User


class IsCourseOwner(BasePermission):
    """Object-level: only the instructor who owns the course (or an admin) may write to it."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.role == User.Role.ADMIN:
            return True
        return obj.instructor.user_id == request.user.id
