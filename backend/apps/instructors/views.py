from rest_framework import generics, permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.accounts.permissions import IsAdminRole, IsInstructor

from .models import InstructorProfile
from .serializers import InstructorModerationSerializer, InstructorProfileSerializer, PublicInstructorSerializer


class PublicInstructorViewSet(viewsets.ReadOnlyModelViewSet):
    """Public, unauthenticated marketing pages — only ever exposes approved profiles."""

    serializer_class = PublicInstructorSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = "slug"
    queryset = InstructorProfile.objects.filter(status=InstructorProfile.Status.APPROVED)


class MyInstructorProfileView(generics.RetrieveUpdateAPIView):
    """Lets the logged-in instructor view/edit their own profile.

    Editing does not re-publish it silently: any change to a previously
    approved profile is not automatically re-gated here for MVP simplicity,
    but new profiles always start `pending_review` (enforced in the model).
    """

    serializer_class = InstructorProfileSerializer
    permission_classes = (permissions.IsAuthenticated, IsInstructor)

    def get_object(self):
        return self.request.user.instructor_profile


class InstructorModerationViewSet(viewsets.ModelViewSet):
    """Admin-only endpoint to approve/reject pending instructor profiles."""

    serializer_class = InstructorModerationSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    queryset = InstructorProfile.objects.all()
    http_method_names = ("get", "patch", "head", "options")

    def perform_update(self, serializer):
        if not self.request.user.is_authenticated or self.request.user.role != "admin":
            raise PermissionDenied()
        serializer.save()
