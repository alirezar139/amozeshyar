from rest_framework.permissions import BasePermission

from .models import User


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.STUDENT)


class IsInstructor(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.INSTRUCTOR)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN)


class IsOwnerOrAdmin(BasePermission):
    """Object-level check: the request user owns the object (via `owner_field`) or is an admin."""

    owner_field = "user"

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.ADMIN:
            return True
        owner = getattr(obj, self.owner_field, None)
        return owner == request.user
