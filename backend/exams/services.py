"""Attempt lifecycle shared by exam, monitoring and admin views."""

from django.conf import settings
from django.utils.timezone import now

from attempt_events.models import AttemptEvent
from attempt_events.services import record_attempt_event

from .models import Answer


def save_answer(attempt, question, value, strict=True):
    """Create or update one answer, validated against its question.

    Returns (answer, created, changed), or None when strict=False and the
    value is unusable.
    """
    defaults = {
        "selected_option": None,
        "text_answer": None,
        "file_upload": None,
        "is_correct": None,
    }

    if question.question_type in ["mcq", "true_false"]:
        option_id = None
        if not isinstance(value, bool):
            try:
                option_id = int(value)
            except (TypeError, ValueError):
                option_id = None
        option = question.options.filter(id=option_id).first() if option_id else None
        if not option:
            if strict:
                raise ValueError("Invalid option for this question")
            return None
        defaults["selected_option"] = option
        defaults["is_correct"] = option.is_correct
    elif question.question_type == "short_answer":
        if not isinstance(value, str):
            if strict:
                raise ValueError("Short answer must be text")
            value = "" if value is None else str(value)
        if len(value) > settings.MAX_SHORT_ANSWER_LENGTH:
            if strict:
                raise ValueError(
                    f"Answer too long (max {settings.MAX_SHORT_ANSWER_LENGTH} characters)"
                )
            return None
        defaults["text_answer"] = value
    # file_upload / image_based: stored as a placeholder answer (not graded).

    existing = Answer.objects.filter(attempt=attempt, question=question).first()
    changed = False
    if existing:
        changed = (
            existing.selected_option_id != getattr(defaults["selected_option"], "id", None)
            or existing.text_answer != defaults["text_answer"]
            or bool(existing.file_upload) != bool(defaults["file_upload"])
        )

    answer, created = Answer.objects.update_or_create(
        attempt=attempt, question=question, defaults=defaults
    )
    return answer, created, changed


def grade_saved_answers(attempt, exam, questions):
    """Recalculate grading from persisted answers."""
    score = 0
    answers = Answer.objects.filter(
        attempt=attempt, question__exam=exam
    ).select_related("question", "selected_option")

    for answer in answers:
        question = answer.question
        is_correct = None
        if question.question_type in ["mcq", "true_false"]:
            is_correct = bool(answer.selected_option and answer.selected_option.is_correct)
            score += question.points if is_correct else -question.negative_points
        elif question.question_type == "short_answer":
            correct = (question.correct_text_answer or "").strip().lower()
            submitted = (answer.text_answer or "").strip().lower()
            is_correct = bool(correct and submitted == correct)
            score += question.points if is_correct else -question.negative_points

        if answer.is_correct != is_correct:
            answer.is_correct = is_correct
            answer.save(update_fields=["is_correct"])

    return score, sum(question.points for question in questions)


# End reasons (ExamAttempt.end_reason)
REASON_SUBMITTED = "submitted"
REASON_DEADLINE = "deadline_expired"
REASON_VIOLATIONS = "violation_threshold"
REASON_ADMIN = "exam_disabled_by_admin"


def finalize_attempt(attempt, status, reason, at_time=None):
    """Grade saved answers and close the attempt. Caller holds the row lock.

    Every way an attempt ends goes through here, so a timeout or a
    termination never silently scores zero.
    """
    questions = list(attempt.exam.questions.all())
    score, total = grade_saved_answers(attempt, attempt.exam, questions)
    attempt.points_scored = score
    attempt.total_points = total
    attempt.status = status
    attempt.end_reason = reason
    attempt.end_time = at_time or now()
    attempt.save(
        update_fields=["points_scored", "total_points", "status", "end_reason", "end_time"]
    )
    record_attempt_event(
        attempt,
        AttemptEvent.EventType.EXAM_SUBMITTED
        if status == "completed"
        else AttemptEvent.EventType.EXAM_TERMINATED,
        metadata={"reason": reason, "points_scored": score, "total_questions": len(questions)},
    )
    return score, total, len(questions)


def expire_if_due(attempt, at_time=None):
    """Auto-submit an expired active attempt. Returns True if it was expired."""
    at_time = at_time or now()
    if attempt.status == "active" and attempt.is_expired(at_time):
        finalize_attempt(attempt, "completed", REASON_DEADLINE, at_time=at_time)
        return True
    return False
