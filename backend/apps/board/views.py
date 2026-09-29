from rest_framework import permissions, viewsets

from apps.accounts.permissions import IsAdminRole

from .models import BoardCard
from .serializers import BoardCardSerializer


class BoardCardViewSet(viewsets.ModelViewSet):
    """The teacher's kanban cards. Moving a card is a PATCH of `column` and `position`."""

    serializer_class = BoardCardSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    pagination_class = None
    queryset = BoardCard.objects.select_related("course")
