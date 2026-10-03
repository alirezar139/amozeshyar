from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("exams/manage", views.ExamManageViewSet, basename="exam-manage")
router.register("exam-questions", views.QuestionManageViewSet, basename="exam-question")
router.register("exam-question-media", views.QuestionMediaViewSet, basename="exam-question-media")
router.register("exam-attempts/manage", views.AttemptManageViewSet, basename="exam-attempt-manage")
router.register("exam-attempts", views.MyAttemptViewSet, basename="exam-attempt")
router.register("exams", views.StudentExamViewSet, basename="exam")

urlpatterns = router.urls
