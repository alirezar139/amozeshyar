"""Exam timing, grading and the result message.

Timing rules (server clock only):
  - an attempt's deadline is fixed at start: the sooner of start + duration
    and the exam's closing time (also re-checked against the closing time
    later, in case the teacher moved it earlier);
  - a timed question's deadline runs from when it was first opened, capped
    by the attempt's deadline;
  - GRACE absorbs network latency for a save sent right at the buzzer.

Grading: choice questions must match the set of correct choices exactly;
short answers match any accepted answer after normalization (Arabic/Persian
letter variants, digits, half-spaces, case and surrounding punctuation);
essays wait for the teacher, unless left empty.
"""
import re
import unicodedata
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Answer, Attempt, Exam, Question

GRACE = timedelta(seconds=5)
MAX_GUIDANCE_LINES = 3

_CHAR_MAP = str.maketrans({
    "ي": "ی", "ى": "ی", "ئ": "ی", "ك": "ک", "ة": "ه", "أ": "ا", "إ": "ا", "آ": "ا", "ؤ": "و",
    "‌": " ", "‏": "", "‎": "", "ـ": "",
    **{str(d): str(i) for i, d in enumerate("۰۱۲۳۴۵۶۷۸۹")},
    **{str(d): str(i) for i, d in enumerate("٠١٢٣٤٥٦٧٨٩")},
})
_DIACRITICS = re.compile(r"[ً-ْٰ]")
_EDGE_PUNCTUATION = " \t\n.,;:!?'\"«»()[]،؛؟-"


def normalize_answer(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").translate(_CHAR_MAP)
    value = _DIACRITICS.sub("", value)
    return " ".join(value.split()).strip(_EDGE_PUNCTUATION).casefold()


def accepted_answers(question: Question) -> list[str]:
    return [a for a in (normalize_answer(line) for line in question.answer_key.splitlines()) if a]


# ---------- timing ----------

def effective_deadline(attempt: Attempt):
    closing = attempt.exam.available_until
    if attempt.deadline and closing:
        return min(attempt.deadline, closing)
    return attempt.deadline or closing


def question_deadline(attempt: Attempt, answer: Answer | None, question: Question):
    """When this question stops accepting answers (None = only the attempt's deadline applies)."""
    if not question.time_limit_seconds or not answer or not answer.opened_at:
        return None
    own = answer.opened_at + timedelta(seconds=question.time_limit_seconds)
    overall = effective_deadline(attempt)
    return min(own, overall) if overall else own


def _past(deadline, now) -> bool:
    return bool(deadline and now > deadline + GRACE)


def start_attempt(exam: Exam, student) -> Attempt:
    existing = Attempt.objects.filter(exam=exam, student=student).first()
    if existing:
        return finalize_if_expired(existing)
    now = timezone.now()
    if not exam.is_open(now):
        raise ValidationError("این آزمون در حال حاضر باز نیست.")
    if not exam.questions.exists():
        raise ValidationError("این آزمون هنوز سوالی ندارد.")
    candidates = [d for d in (
        now + timedelta(minutes=exam.duration_minutes) if exam.duration_minutes else None,
        exam.available_until,
    ) if d]
    attempt, _ = Attempt.objects.get_or_create(
        exam=exam, student=student, defaults={"deadline": min(candidates) if candidates else None}
    )
    return attempt


def finalize_if_expired(attempt: Attempt) -> Attempt:
    if attempt.status == Attempt.Status.IN_PROGRESS and _past(effective_deadline(attempt), timezone.now()):
        submit_attempt(attempt, Attempt.SubmitReason.TIMEOUT)
        attempt.refresh_from_db()
    return attempt


def _ensure_writable(attempt: Attempt) -> None:
    finalize_if_expired(attempt)
    if attempt.status != Attempt.Status.IN_PROGRESS:
        raise ValidationError({"detail": "زمان آزمون تمام شده و پاسخ‌ها ارسال شده‌اند.", "code": "attempt_closed"})


def open_question(attempt: Attempt, question: Question) -> Answer:
    _ensure_writable(attempt)
    answer, _ = Answer.objects.get_or_create(attempt=attempt, question=question)
    if answer.opened_at is None:
        answer.opened_at = timezone.now()
        answer.save(update_fields=["opened_at", "updated_at"])
    return answer


def writable_answer(attempt: Attempt, question: Question) -> Answer:
    """The answer row for saving into, after every timing check."""
    _ensure_writable(attempt)
    answer, _ = Answer.objects.get_or_create(attempt=attempt, question=question)
    if question.time_limit_seconds:
        if answer.opened_at is None:
            raise ValidationError("این سوال هنوز باز نشده است.")
        if _past(question_deadline(attempt, answer, question), timezone.now()):
            raise ValidationError({"detail": "زمان این سوال تمام شده است.", "code": "question_closed"})
    return answer


def save_answer(attempt: Attempt, question: Question, choice_ids: list[int] | None, text: str | None) -> Answer:
    answer = writable_answer(attempt, question)
    if choice_ids is not None:
        if question.kind not in Question.CHOICE_KINDS:
            raise ValidationError("این سوال گزینه‌ای نیست.")
        choices = list(question.choices.filter(pk__in=choice_ids))
        if len(choices) != len(set(choice_ids)):
            raise ValidationError("گزینه‌ی نامعتبر.")
        if question.kind != Question.Kind.MULTIPLE_CHOICE and len(choices) > 1:
            raise ValidationError("برای این سوال فقط یک گزینه را می‌توان انتخاب کرد.")
        answer.selected_choices.set(choices)
    if text is not None:
        if question.kind in Question.CHOICE_KINDS:
            raise ValidationError("این سوال پاسخ متنی ندارد.")
        answer.text = text
        answer.save(update_fields=["text", "updated_at"])
    return answer


# ---------- grading ----------

def _grade_answer(answer: Answer) -> None:
    question = answer.question
    if question.kind in Question.CHOICE_KINDS:
        chosen = set(answer.selected_choices.values_list("pk", flat=True))
        correct = {c.pk for c in question.choices.all() if c.is_correct}
        answer.is_correct = bool(chosen) and chosen == correct
    elif question.kind == Question.Kind.SHORT_ANSWER:
        given = normalize_answer(answer.text)
        answer.is_correct = bool(given) and given in accepted_answers(question)
    else:  # essay: the teacher grades it — unless there's nothing to grade
        if answer.text.strip() or answer.files.exists():
            return
        answer.is_correct = False
    answer.score = question.points if answer.is_correct else Decimal(0)


def submit_attempt(attempt: Attempt, reason: str) -> Attempt:
    with transaction.atomic():
        attempt = Attempt.objects.select_for_update().select_related("exam").get(pk=attempt.pk)
        if attempt.status != Attempt.Status.IN_PROGRESS:
            return attempt
        now = timezone.now()
        deadline = effective_deadline(attempt)
        attempt.submitted_at = min(now, deadline) if deadline and reason == Attempt.SubmitReason.TIMEOUT else now
        attempt.submit_reason = reason
        attempt.status = Attempt.Status.SUBMITTED
        attempt.save(update_fields=["submitted_at", "submit_reason", "status", "updated_at"])

        questions = list(attempt.exam.questions.prefetch_related("choices"))
        existing = {a.question_id: a for a in attempt.answers.all()}
        Answer.objects.bulk_create(
            [Answer(attempt=attempt, question=q) for q in questions if q.pk not in existing]
        )
        for answer in attempt.answers.select_related("question").prefetch_related("question__choices", "files"):
            _grade_answer(answer)
            answer.save(update_fields=["is_correct", "score", "updated_at"])
    return recompute_attempt(attempt)


def recompute_attempt(attempt: Attempt) -> Attempt:
    """Totals and status from the current answer grades; sends the result
    message the first time the attempt becomes fully graded."""
    answers = list(attempt.answers.select_related("question"))
    attempt.score = sum((a.score or Decimal(0) for a in answers), Decimal(0))
    attempt.max_score = sum((a.question.points for a in answers), Decimal(0))
    pending = any(a.score is None for a in answers)
    attempt.status = Attempt.Status.SUBMITTED if pending else Attempt.Status.GRADED
    attempt.save(update_fields=["score", "max_score", "status", "updated_at"])
    if attempt.status == Attempt.Status.GRADED and attempt.exam.notify_by_message and not attempt.result_notified_at:
        notify_result(attempt)
    return attempt


def grade_essay(answer: Answer, score: Decimal, feedback: str) -> Answer:
    if score < 0 or score > answer.question.points:
        raise ValidationError({"score": f"نمره باید بین ۰ و {fa_number(answer.question.points)} باشد."})
    answer.score = score
    answer.is_correct = score >= answer.question.points
    answer.teacher_feedback = feedback
    answer.save(update_fields=["score", "is_correct", "teacher_feedback", "updated_at"])
    recompute_attempt(answer.attempt)
    return answer


# ---------- result message ----------

def fa_number(value) -> str:
    if isinstance(value, Decimal):
        value = value.quantize(Decimal("0.01")).normalize()
        value = f"{value:f}"
    return str(value).translate(str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹٫"))


def result_verdict(attempt: Attempt) -> str:
    if attempt.percent >= 90:
        return "عالی بود! 🎉"
    if attempt.percent >= attempt.exam.pass_percent:
        return "قبول شدید 👏"
    return f"هنوز به حد قبولی ({fa_number(attempt.exam.pass_percent)}٪) نرسیده‌اید؛ پاسخ‌نامه را مرور کنید."


def _short(text: str, limit: int = 140) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def result_message(attempt: Attempt) -> str:
    exam = attempt.exam
    answers = list(attempt.answers.select_related("question").order_by("question__order", "question_id"))
    numbers = {q_id: i for i, q_id in enumerate(exam.questions.values_list("pk", flat=True), start=1)}
    wrong = [a for a in answers if not a.is_correct]
    lines = [
        f"📝 نتیجه‌ی آزمون «{exam.title}»",
        f"نمره‌ی شما: {fa_number(attempt.score)} از {fa_number(attempt.max_score)} ({fa_number(attempt.percent)}٪) — {result_verdict(attempt)}",
        f"{fa_number(len(answers) - len(wrong))} پاسخ درست و {fa_number(len(wrong))} پاسخ نادرست یا بی‌پاسخ.",
    ]
    guidance = [
        (a, a.teacher_feedback or a.question.explanation) for a in wrong if a.teacher_feedback or a.question.explanation
    ]
    if guidance:
        lines.append("نکته‌هایی برای مرور:")
        for answer, note in guidance[:MAX_GUIDANCE_LINES]:
            lines.append(f"• سوال {fa_number(numbers.get(answer.question_id, ''))}: {_short(note)}")
        if len(guidance) > MAX_GUIDANCE_LINES:
            lines.append(f"و {fa_number(len(guidance) - MAX_GUIDANCE_LINES)} نکته‌ی دیگر در صفحه‌ی آزمون.")
    elif not wrong:
        lines.append("همه‌ی پاسخ‌ها درست بود؛ آفرین! 🌟")
    lines.append("پاسخ‌نامه‌ی کامل در بخش «آزمون‌ها»ی داشبورد شماست.")
    return "\n".join(lines)


def notify_result(attempt: Attempt) -> None:
    from apps.messaging.services import send_bot_message

    if send_bot_message(attempt.student, result_message(attempt), bot="exam"):
        attempt.result_notified_at = timezone.now()
        attempt.save(update_fields=["result_notified_at", "updated_at"])
