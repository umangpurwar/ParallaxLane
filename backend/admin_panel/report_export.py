"""CSV export helpers for raw examination data."""

import csv
from io import StringIO

from django.utils import timezone

from exams.models import ExamAttempt


CSV_FIELDS = [
    "record_type", "exam_id", "exam_title", "organisation_id", "organisation_name",
    "attempt_id", "candidate_id", "candidate_name", "candidate_email", "attempt_status",
    "attempt_start_time", "attempt_deadline", "attempt_end_time", "points_scored",
    "total_points", "percentage", "risk_score", "total_violations", "question_id",
    "question_text", "question_type", "answer_id", "selected_option_id",
    "selected_option_text", "text_answer", "file_upload", "is_correct", "violation_id",
    "violation_type", "violation_severity", "violation_timestamp", "violation_metadata",
    "event_id", "event_type", "event_timestamp", "event_question_id", "event_metadata",
]


def _isoformat(value):
    if not value:
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.isoformat()


def _candidate_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.name or user.email or user.username


def _percentage(attempt):
    if not attempt.total_points:
        return "0"
    return round((float(attempt.points_scored or 0) / float(attempt.total_points)) * 100, 1)


def _base_row(attempt, record_type):
    exam = attempt.exam
    user = attempt.user
    return {
        "record_type": record_type,
        "exam_id": exam.id,
        "exam_title": exam.title,
        "organisation_id": exam.organisation_id,
        "organisation_name": exam.organisation.name,
        "attempt_id": attempt.id,
        "candidate_id": user.id,
        "candidate_name": _candidate_name(user),
        "candidate_email": user.email or user.username,
        "attempt_status": attempt.status,
        "attempt_start_time": _isoformat(attempt.start_time),
        "attempt_deadline": _isoformat(attempt.deadline),
        "attempt_end_time": _isoformat(attempt.end_time),
        "points_scored": attempt.points_scored,
        "total_points": attempt.total_points,
        "percentage": _percentage(attempt),
        "risk_score": attempt.risk_score,
        "total_violations": attempt.total_violations,
    }


def _rows_for_attempt(attempt):
    yield _base_row(attempt, "attempt")

    for answer in attempt.answers.select_related("question", "selected_option").all():
        row = _base_row(attempt, "answer")
        row.update({
            "question_id": answer.question_id,
            "question_text": answer.question.text,
            "question_type": answer.question.question_type,
            "answer_id": answer.id,
            "selected_option_id": answer.selected_option_id,
            "selected_option_text": answer.selected_option.text if answer.selected_option else "",
            "text_answer": answer.text_answer or "",
            "file_upload": answer.file_upload.name if answer.file_upload else "",
            "is_correct": answer.is_correct,
        })
        yield row

    for violation in attempt.violations.all():
        row = _base_row(attempt, "violation")
        row.update({
            "violation_id": violation.id,
            "violation_type": violation.violation_type,
            "violation_severity": violation.severity,
            "violation_timestamp": _isoformat(violation.timestamp),
            "violation_metadata": violation.metadata or {},
        })
        yield row

    for event in attempt.events.select_related("question").all():
        row = _base_row(attempt, "attempt_event")
        row.update({
            "event_id": event.id,
            "event_type": event.event_type,
            "event_timestamp": _isoformat(event.timestamp),
            "event_question_id": event.question_id,
            "event_metadata": event.metadata or {},
        })
        yield row


def generate_assessment_csv(exam):
    """Return UTF-8 CSV containing raw attempts and related examination data."""
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()

    attempts = (
        ExamAttempt.objects.filter(exam=exam)
        .select_related("user", "exam", "exam__organisation")
        .prefetch_related(
            "answers__question", "answers__selected_option", "violations", "events"
        )
        .order_by("id")
    )
    for attempt in attempts:
        for row in _rows_for_attempt(attempt):
            writer.writerow(row)

    return buffer.getvalue()
