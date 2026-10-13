from rest_framework.permissions import BasePermission


class IsDeveloper(BasePermission):
    """The developer account (a superuser hidden from the instructor's user list)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
