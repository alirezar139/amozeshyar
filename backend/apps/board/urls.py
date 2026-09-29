from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("board/cards", views.BoardCardViewSet, basename="board-card")

urlpatterns = router.urls
