from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from . import services
from .models import Attempt, Choice, Exam, MediaKind, Question, QuestionMedia

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
AUDIO_EXTENSIONS = {"webm", "ogg", "oga", "m4a", "mp4", "mp3", "wav", "aac"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_AUDIO_BYTES = 30 * 1024 * 1024
# Media links have to outlive a long exam, unlike the usual 10-minute ones.
MEDIA_URL_SECONDS = 4 * 3600


def media_kind(upload) -> str:
    """The upload's kind (image/audio) after checking its type and size."""
    name = upload.name or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in IMAGE_EXTENSIONS:
        if upload.size > MAX_IMAGE_BYTES:
            raise serializers.ValidationError({"file": "حجم عکس بیشتر از ۱۰ مگابایت است."})
        return MediaKind.IMAGE
    if ext in AUDIO_EXTENSIONS:
        if upload.size > MAX_AUDIO_BYTES:
            raise serializers.ValidationError({"file": "حجم فایل صوتی بیشتر از ۳۰ مگابایت است."})
        return MediaKind.AUDIO
    raise serializers.ValidationError({"file": "فقط عکس (jpg, png, webp, gif) یا صوت (mp3, m4a, ogg, webm, wav) مجاز است."})


def file_url(field) -> str | None:
    if not field:
        return None
    if hasattr(field.storage, "bucket"):  # S3/MinIO: a signed link
        from apps.videos.services.signing import get_presigned_url

        return get_presigned_url(field.name, expires_in=MEDIA_URL_SECONDS)
    return field.url


def media_payload(item) -> dict:
    return {
        "id": item.id,
        "kind": item.kind,
        "url": file_url(item.file),
        "name": item.original_name,
        **({"role": item.role} if isinstance(item, QuestionMedia) else {"duration_seconds": item.duration_seconds}),
    }


# ---------- teacher ----------

class ChoiceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Choice
        fields = ("id", "text", "is_correct", "order")


class QuestionMediaUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = QuestionMedia
        fields = ("id", "question", "role", "file")

    def validate(self, attrs):
        attrs["kind"] = media_kind(attrs["file"])
        return attrs

    def create(self, validated_data):
        upload = validated_data["file"]
        return QuestionMedia.objects.create(**validated_data, original_name=upload.name[:255])

    def to_representation(self, instance):
        return media_payload(instance)


class QuestionManageSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)
    media = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = (
            "id", "exam", "order", "kind", "text", "example", "answer_key", "explanation",
            "points", "time_limit_seconds", "choices", "media",
        )
        read_only_fields = ("order",)

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None and not isinstance(self.instance, list):
            fields["exam"].read_only = True
        return fields

    def get_media(self, obj) -> list[dict]:
        return [media_payload(m) for m in obj.media.all()]

    def validate_points(self, value):
        if value <= 0:
            raise serializers.ValidationError("نمره‌ی سوال باید بیشتر از صفر باشد.")
        return value

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        if kind in Question.CHOICE_KINDS:
            choices = attrs.get("choices")
            if choices is None and self.instance is not None:
                choices = [{"is_correct": c.is_correct} for c in self.instance.choices.all()]
            choices = [c for c in choices or [] if c.get("text", "x").strip()]
            correct = sum(1 for c in choices if c.get("is_correct"))
            if len(choices) < 2:
                raise serializers.ValidationError({"choices": "حداقل دو گزینه لازم است."})
            if correct == 0:
                raise serializers.ValidationError({"choices": "گزینه‌ی درست را مشخص کنید."})
            if kind != Question.Kind.MULTIPLE_CHOICE and correct > 1:
                raise serializers.ValidationError({"choices": "این نوع سوال فقط یک گزینه‌ی درست دارد."})
        if kind == Question.Kind.SHORT_ANSWER:
            key = attrs.get("answer_key", getattr(self.instance, "answer_key", ""))
            if not key.strip():
                raise serializers.ValidationError({"answer_key": "حداقل یک پاسخ قابل‌قبول در پاسخ‌نامه بنویسید."})
        return attrs

    def _save_choices(self, question, choices):
        if choices is None:
            return
        if question.kind not in Question.CHOICE_KINDS:
            question.choices.all().delete()
            return
        keep = []
        for index, data in enumerate(c for c in choices if c.get("text", "").strip()):
            fields = {"text": data["text"].strip(), "is_correct": data.get("is_correct", False), "order": index}
            choice = question.choices.filter(pk=data.get("id")).first() if data.get("id") else None
            if choice:
                for key, value in fields.items():
                    setattr(choice, key, value)
                choice.save()
            else:
                choice = Choice.objects.create(question=question, **fields)
            keep.append(choice.pk)
        question.choices.exclude(pk__in=keep).delete()

    @transaction.atomic
    def create(self, validated_data):
        choices = validated_data.pop("choices", None)
        question = super().create(validated_data)
        self._save_choices(question, choices)
        return question

    @transaction.atomic
    def update(self, instance, validated_data):
        choices = validated_data.pop("choices", None)
        question = super().update(instance, validated_data)
        if choices is None and question.kind not in Question.CHOICE_KINDS:
            choices = []  # switched away from a choice kind: drop old options
        self._save_choices(question, choices)
        return question


class ExamManageSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    question_count = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = (
            "id", "course", "course_title", "title", "description", "status",
            "available_from", "available_until", "duration_minutes", "pass_percent", "notify_by_message",
            "question_count", "total_points", "attempt_count", "pending_count", "created_at",
        )

    def get_question_count(self, obj) -> int:
        return len(obj.questions.all())

    def get_total_points(self, obj) -> float:
        return float(sum(q.points for q in obj.questions.all()))

    def get_attempt_count(self, obj) -> int:
        return len(obj.attempts.all())

    def get_pending_count(self, obj) -> int:
        return sum(1 for a in obj.attempts.all() if a.status == Attempt.Status.SUBMITTED)

    def validate_pass_percent(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("حد قبولی باید بین ۰ تا ۱۰۰ باشد.")
        return value

    def validate(self, attrs):
        start = attrs.get("available_from", getattr(self.instance, "available_from", None))
        end = attrs.get("available_until", getattr(self.instance, "available_until", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"available_until": "زمان بسته‌شدن باید بعد از زمان شروع باشد."})
        if attrs.get("status") == Exam.Status.PUBLISHED:
            exam = self.instance
            if exam is None or not exam.questions.exists():
                raise serializers.ValidationError({"status": "آزمون بدون سوال را نمی‌توان منتشر کرد."})
        return attrs


class ExamManageDetailSerializer(ExamManageSerializer):
    questions = QuestionManageSerializer(many=True, read_only=True)

    class Meta(ExamManageSerializer.Meta):
        fields = (*ExamManageSerializer.Meta.fields, "questions")


class AttemptSummarySerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(source="student.email", read_only=True)
    percent = serializers.FloatField(read_only=True)
    pending_count = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = (
            "id", "student", "student_name", "student_email", "status", "score", "max_score", "percent",
            "started_at", "submitted_at", "submit_reason", "pending_count",
        )

    def get_student_name(self, obj) -> str:
        return obj.student.get_full_name() or obj.student.email.split("@")[0]

    def get_pending_count(self, obj) -> int:
        return sum(1 for a in obj.answers.all() if a.score is None) if obj.is_finished else 0


# ---------- student ----------

class StudentExamSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    question_count = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()
    my_attempt = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = (
            "id", "course", "course_title", "title", "description", "available_from", "available_until",
            "duration_minutes", "pass_percent", "question_count", "total_points", "is_open", "my_attempt",
        )

    def get_question_count(self, obj) -> int:
        return len(obj.questions.all())

    def get_total_points(self, obj) -> float:
        return float(sum(q.points for q in obj.questions.all()))

    def get_is_open(self, obj) -> bool:
        return obj.is_open()

    def get_my_attempt(self, obj) -> dict | None:
        attempts = [a for a in obj.attempts.all() if a.student_id == self.context["request"].user.id]
        if not attempts:
            return None
        attempt = services.finalize_if_expired(attempts[0])
        return {
            "id": attempt.id, "status": attempt.status, "score": attempt.score,
            "max_score": attempt.max_score, "percent": attempt.percent,
        }


class AttemptSerializer(serializers.Serializer):
    """One attempt with its questions, for the student taking it (answer key
    hidden until it's submitted) and for results/grading (`reveal`)."""

    def to_representation(self, attempt: Attempt):
        exam = attempt.exam
        reveal = attempt.is_finished
        answers = {a.question_id: a for a in attempt.answers.all()}
        questions = []
        for number, question in enumerate(exam.questions.all(), start=1):
            answer = answers.get(question.id)
            q_deadline = services.question_deadline(attempt, answer, question)
            item = {
                "id": question.id,
                "number": number,
                "kind": question.kind,
                "text": question.text,
                "example": question.example,
                "points": question.points,
                "time_limit_seconds": question.time_limit_seconds,
                "deadline": q_deadline,
                "media": [media_payload(m) for m in question.media.all() if m.role == QuestionMedia.Role.PROMPT],
                "choices": [{"id": c.id, "text": c.text} for c in question.choices.all()],
                "answer": {
                    "opened_at": answer.opened_at if answer else None,
                    "selected_choices": [c.id for c in answer.selected_choices.all()] if answer else [],
                    "text": answer.text if answer else "",
                    "files": [media_payload(f) for f in answer.files.all()] if answer else [],
                },
            }
            if reveal:
                item.update(
                    is_correct=answer.is_correct if answer else False,
                    score=answer.score if answer else 0,
                    teacher_feedback=answer.teacher_feedback if answer else "",
                    answer_id=answer.id if answer else None,
                    correct_choices=[c.id for c in question.choices.all() if c.is_correct],
                    answer_key=question.answer_key,
                    explanation=question.explanation,
                    answer_media=[media_payload(m) for m in question.media.all() if m.role == QuestionMedia.Role.ANSWER],
                )
            questions.append(item)

        data = {
            "id": attempt.id,
            "exam": {
                "id": exam.id, "title": exam.title, "description": exam.description,
                "course_title": exam.course.title, "pass_percent": exam.pass_percent,
                "duration_minutes": exam.duration_minutes, "notify_by_message": exam.notify_by_message,
            },
            "student_name": attempt.student.get_full_name() or attempt.student.email,
            "status": attempt.status,
            "started_at": attempt.started_at,
            "deadline": services.effective_deadline(attempt),
            "submitted_at": attempt.submitted_at,
            "submit_reason": attempt.submit_reason,
            "server_now": timezone.now(),
            "questions": questions,
        }
        if reveal:
            data.update(
                score=attempt.score,
                max_score=attempt.max_score,
                percent=attempt.percent,
                passed=attempt.percent >= exam.pass_percent,
                verdict=services.result_verdict(attempt) if attempt.status == Attempt.Status.GRADED else "",
            )
        return data
