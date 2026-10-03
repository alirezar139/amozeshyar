"""Timed exams for a course.

The teacher builds an exam out of questions; each question has its text, an
optional worked example, optional image/audio attachments, an answer key
(choices marked correct, accepted short answers, or a model answer) and a
guidance note shown to students who got it wrong.

A student gets one attempt per exam. The server's clock is the only one that
counts: the attempt's `deadline` is fixed when it starts, a timed question's
clock starts when the student first opens it, and answers arriving after
either deadline are refused. An attempt that runs out of time without being
submitted is finalized the next time anyone looks at it (see services).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.courses.models import Course


class MediaKind(models.TextChoices):
    IMAGE = "image", "Image"
    AUDIO = "audio", "Audio"


class Exam(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="exams")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    # Window in which the exam can be started; both optional. Once
    # `available_until` passes, the exam closes — running attempts included.
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    # Total time for one attempt; null = no overall limit.
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    pass_percent = models.PositiveSmallIntegerField(default=60)
    # Send the student a messenger message with their score once graded.
    notify_by_message = models.BooleanField(default=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.title

    def is_open(self, now=None) -> bool:
        now = now or timezone.now()
        if self.status != self.Status.PUBLISHED:
            return False
        if self.available_from and now < self.available_from:
            return False
        return not (self.available_until and now >= self.available_until)


class Question(TimeStampedModel):
    class Kind(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "Single choice"
        MULTIPLE_CHOICE = "multiple_choice", "Multiple choice"
        TRUE_FALSE = "true_false", "True / false"
        SHORT_ANSWER = "short_answer", "Short answer"
        # Free text and/or image/audio uploads; graded by the teacher.
        ESSAY = "essay", "Essay / file"

    CHOICE_KINDS = (Kind.SINGLE_CHOICE, Kind.MULTIPLE_CHOICE, Kind.TRUE_FALSE)

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField(default=0)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SINGLE_CHOICE)
    text = models.TextField()
    example = models.TextField(blank=True)
    # Short answer: accepted answers, one per line. Essay: the model answer
    # shown to the student after grading. Unused for choice questions.
    answer_key = models.TextField(blank=True)
    # Shown to the student after the exam when they got this one wrong.
    explanation = models.TextField(blank=True)
    points = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    # Own clock for this question, counted from when it's first opened.
    time_limit_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("exam", "order", "id")

    def __str__(self):
        return f"{self.exam.title} #{self.order}"

    @property
    def is_auto_graded(self) -> bool:
        return self.kind != self.Kind.ESSAY


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=1000)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("question", "order", "id")

    def __str__(self):
        return self.text


class QuestionMedia(TimeStampedModel):
    """An image or audio clip the teacher attached to a question: part of the
    question itself (`prompt`), or of its answer key (`answer`, only shown
    after the attempt is submitted)."""

    class Role(models.TextChoices):
        PROMPT = "prompt", "Question"
        ANSWER = "answer", "Answer key"

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="media")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PROMPT)
    kind = models.CharField(max_length=10, choices=MediaKind.choices)
    file = models.FileField(upload_to="exam_media/")
    original_name = models.CharField(max_length=255)

    class Meta:
        ordering = ("created_at", "id")


class Attempt(TimeStampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        # Submitted, but some essay answers still wait for the teacher.
        SUBMITTED = "submitted", "Awaiting grading"
        GRADED = "graded", "Graded"

    class SubmitReason(models.TextChoices):
        STUDENT = "student", "Submitted by the student"
        TIMEOUT = "timeout", "Time ran out"

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_attempts")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    # null = no time limit at all (no duration and no closing time).
    deadline = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    submit_reason = models.CharField(max_length=10, choices=SubmitReason.choices, blank=True)
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    result_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-started_at",)
        constraints = [models.UniqueConstraint(fields=("exam", "student"), name="one_attempt_per_student")]

    def __str__(self):
        return f"{self.student} — {self.exam}"

    @property
    def is_finished(self) -> bool:
        return self.status != self.Status.IN_PROGRESS

    @property
    def percent(self) -> float:
        return round(float(self.score) * 100 / float(self.max_score), 1) if self.max_score else 0.0


class Answer(TimeStampedModel):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    # When the student first opened this question (starts a timed question's clock).
    opened_at = models.DateTimeField(null=True, blank=True)
    selected_choices = models.ManyToManyField(Choice, blank=True, related_name="+")
    text = models.TextField(blank=True)
    # Set by grading: null until graded (essays wait for the teacher).
    is_correct = models.BooleanField(null=True, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    teacher_feedback = models.TextField(blank=True)

    class Meta:
        ordering = ("question__order", "question_id")
        constraints = [models.UniqueConstraint(fields=("attempt", "question"), name="one_answer_per_question")]


class AnswerFile(TimeStampedModel):
    """An image or voice recording the student attached to an essay answer."""

    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="files")
    kind = models.CharField(max_length=10, choices=MediaKind.choices)
    file = models.FileField(upload_to="exam_answers/")
    original_name = models.CharField(max_length=255)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("created_at", "id")
