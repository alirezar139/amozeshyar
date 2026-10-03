from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Max, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.authentication import UploadJWTAuthentication
from apps.accounts.permissions import IsAdminRole

from . import services
from .models import Answer, AnswerFile, Attempt, Exam, Question, QuestionMedia
from .serializers import (
    AttemptSerializer,
    AttemptSummarySerializer,
    ExamManageDetailSerializer,
    ExamManageSerializer,
    QuestionManageSerializer,
    QuestionMediaUploadSerializer,
    StudentExamSerializer,
    media_kind,
    media_payload,
)


def _attempt_queryset():
    return Attempt.objects.select_related("exam__course", "student").prefetch_related(
        Prefetch("exam__questions", queryset=Question.objects.prefetch_related("choices", "media")),
        Prefetch("answers", queryset=Answer.objects.prefetch_related("selected_choices", "files")),
    )


def _attempt_response(attempt: Attempt, **kwargs) -> Response:
    return Response(AttemptSerializer(_attempt_queryset().get(pk=attempt.pk)).data, **kwargs)


# ---------- teacher ----------

class ExamManageViewSet(viewsets.ModelViewSet):
    """Admin (the teacher): exams of every course (`?course=`), with their
    questions on retrieve; `attempts` lists who took one and how they did."""

    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    pagination_class = None

    def get_queryset(self):
        exams = Exam.objects.select_related("course").prefetch_related(
            Prefetch("questions", queryset=Question.objects.prefetch_related("choices", "media")), "attempts"
        )
        course_id = self.request.query_params.get("course")
        return exams.filter(course_id=course_id) if course_id else exams

    def get_serializer_class(self):
        return ExamManageDetailSerializer if self.action == "retrieve" else ExamManageSerializer

    @action(detail=True, methods=["get"])
    def attempts(self, request, pk=None):
        exam = self.get_object()
        attempts = exam.attempts.select_related("student", "exam").prefetch_related("answers")
        for attempt in attempts:
            services.finalize_if_expired(attempt)
        return Response(AttemptSummarySerializer(attempts.all(), many=True).data)


class QuestionManageViewSet(viewsets.ModelViewSet):
    """Admin CRUD for an exam's questions (`?exam=`), choices written inline."""

    serializer_class = QuestionManageSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    pagination_class = None

    def get_queryset(self):
        questions = Question.objects.prefetch_related("choices", "media")
        exam_id = self.request.query_params.get("exam")
        return questions.filter(exam_id=exam_id) if exam_id else questions

    def perform_create(self, serializer):
        exam = serializer.validated_data["exam"]
        serializer.save(order=(exam.questions.aggregate(m=Max("order"))["m"] or 0) + 1)

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        """Swap with the neighbour: body {"direction": "up" | "down"}."""
        question = self.get_object()
        siblings = Question.objects.filter(exam=question.exam)
        if request.data.get("direction") == "up":
            neighbour = siblings.filter(order__lt=question.order).order_by("-order").first()
        else:
            neighbour = siblings.filter(order__gt=question.order).order_by("order").first()
        if neighbour:
            with transaction.atomic():
                Question.objects.filter(pk=question.pk).update(order=neighbour.order)
                Question.objects.filter(pk=neighbour.pk).update(order=question.order)
        return Response(self.get_serializer(self.get_queryset().filter(exam=question.exam), many=True).data)


class QuestionMediaViewSet(mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Admin: attach an image/audio clip to a question or its answer key."""

    serializer_class = QuestionMediaUploadSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    queryset = QuestionMedia.objects.all()

    def get_authenticators(self):
        if self.request and self.request.method == "POST":
            return [UploadJWTAuthentication()]
        return super().get_authenticators()


class AttemptManageViewSet(mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Admin: one attempt in full, grading its essay answers, and deleting it
    (which lets the student take the exam again)."""

    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    serializer_class = AttemptSerializer

    def get_queryset(self):
        return _attempt_queryset()

    def retrieve(self, request, *args, **kwargs):
        attempt = services.finalize_if_expired(self.get_object())
        return _attempt_response(attempt)

    @action(detail=True, methods=["post"])
    def grade(self, request, pk=None):
        """Body {"answer": id, "score": number, "feedback": "..."}."""
        attempt = services.finalize_if_expired(self.get_object())
        if not attempt.is_finished:
            raise ValidationError("این آزمون هنوز در حال برگزاری است.")
        answer = get_object_or_404(attempt.answers.select_related("question", "attempt__exam"), pk=request.data.get("answer"))
        try:
            score = Decimal(str(request.data.get("score")))
        except (InvalidOperation, ValueError):
            raise ValidationError({"score": "نمره را وارد کنید."}) from None
        services.grade_essay(answer, score, str(request.data.get("feedback", ""))[:4000])
        return _attempt_response(attempt)


# ---------- student ----------

def _enrolled(user, course_id) -> bool:
    return user.enrollments.filter(course_id=course_id, is_active=True).exists()


class StudentExamViewSet(viewsets.ReadOnlyModelViewSet):
    """Published exams of the student's active courses (`?course=`). The
    questions themselves only come with an attempt, once it's started."""

    serializer_class = StudentExamSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Exam.objects.none()
        user = self.request.user
        exams = (
            Exam.objects.filter(
                status=Exam.Status.PUBLISHED,
                course__enrollments__student=user,
                course__enrollments__is_active=True,
            )
            .select_related("course")
            .prefetch_related("questions", Prefetch("attempts", queryset=Attempt.objects.filter(student=user).select_related("exam")))
            .distinct()
        )
        course_id = self.request.query_params.get("course")
        return exams.filter(course_id=course_id) if course_id else exams

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Start (or resume) the student's attempt."""
        exam = self.get_object()
        if not _enrolled(request.user, exam.course_id):
            raise ValidationError("برای شرکت در این آزمون باید در دوره ثبت‌نام کرده باشید.")
        attempt = services.start_attempt(exam, request.user)
        return _attempt_response(attempt, status=status.HTTP_201_CREATED)


class MyAttemptViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """The student's own attempt: open a question (starts its clock), save
    answers and files, and submit. Results come back once it's submitted."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = AttemptSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Attempt.objects.none()
        return _attempt_queryset().filter(student=self.request.user)

    def get_authenticators(self):
        if self.request and self.request.method == "POST" and self.request.path.rstrip("/").endswith("files"):
            return [UploadJWTAuthentication()]
        return super().get_authenticators()

    def _question(self, attempt: Attempt, question_id) -> Question:
        return get_object_or_404(Question.objects.prefetch_related("choices"), pk=question_id, exam=attempt.exam)

    def retrieve(self, request, *args, **kwargs):
        attempt = services.finalize_if_expired(self.get_object())
        return _attempt_response(attempt)

    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        attempt = self.get_object()
        answer = services.open_question(attempt, self._question(attempt, request.data.get("question")))
        return Response({
            "question": answer.question_id,
            "opened_at": answer.opened_at,
            "deadline": services.question_deadline(attempt, answer, answer.question),
        })

    @action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        """Body {"question": id, "choices": [ids]} or {"question": id, "text": "..."}."""
        attempt = self.get_object()
        question = self._question(attempt, request.data.get("question"))
        choices = request.data.get("choices")
        if choices is not None and not (isinstance(choices, list) and all(isinstance(c, int) for c in choices)):
            raise ValidationError({"choices": "فهرست گزینه‌ها نامعتبر است."})
        text = request.data.get("text")
        answer = services.save_answer(attempt, question, choices, str(text)[:20000] if text is not None else None)
        return Response({"question": question.id, "saved_at": answer.updated_at})

    @action(detail=True, methods=["post"])
    def files(self, request, pk=None):
        """Multipart {question, file, duration_seconds?}: an image/voice for an essay answer."""
        attempt = self.get_object()
        question = self._question(attempt, request.data.get("question"))
        if question.kind != Question.Kind.ESSAY:
            raise ValidationError("برای این سوال نمی‌توان فایل فرستاد.")
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "فایلی انتخاب نشده است."})
        kind = media_kind(upload)
        answer = services.writable_answer(attempt, question)
        if answer.files.count() >= 5:
            raise ValidationError("برای هر سوال حداکثر ۵ فایل می‌توان فرستاد.")
        duration = request.data.get("duration_seconds")
        item = AnswerFile.objects.create(
            answer=answer, kind=kind, file=upload, original_name=upload.name[:255],
            duration_seconds=int(duration) if str(duration or "").isdigit() else None,
        )
        return Response(media_payload(item), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"files/(?P<file_id>\d+)")
    def delete_file(self, request, pk=None, file_id=None):
        attempt = self.get_object()
        item = get_object_or_404(AnswerFile.objects.select_related("answer__question"), pk=file_id, answer__attempt=attempt)
        services.writable_answer(attempt, item.answer.question)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        attempt = services.finalize_if_expired(self.get_object())
        deadline = services.effective_deadline(attempt)
        # The page submits on its own when the clock hits zero: that's a timeout, not a choice.
        reason = Attempt.SubmitReason.TIMEOUT if deadline and timezone.now() >= deadline else Attempt.SubmitReason.STUDENT
        services.submit_attempt(attempt, reason)
        return _attempt_response(attempt)
