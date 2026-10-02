"""Violation rules and recording."""

from django.db.models import F

from exams.services import REASON_VIOLATIONS, finalize_attempt

from .models import Violation

# type: (severity, counts_toward_violation_limit)
# Soft signals (False) raise the risk score for invigilator review but never
# auto-terminate: flaky Wi-Fi or a notification pull must not end an exam.
VIOLATION_RULES = {
    # web client (legacy)
    "tab_switch": (2, True),
    "window_blur": (1, False),
    "copy_paste": (3, True),
    # Android client
    "app_backgrounded": (3, True),
    "lock_task_exited": (5, True),
    "multi_window": (4, True),
    "overlay_detected": (4, True),
    "screen_capture": (4, True),
    "debugger_attached": (5, True),
    "accessibility_service": (2, False),
    "root_suspected": (2, False),
    "clock_tamper": (2, False),
    # server-generated
    "heartbeat_gap": (1, False),
    "integrity_failed": (5, True),
}

CLIENT_REPORTABLE = set(VIOLATION_RULES) - {"heartbeat_gap", "integrity_failed"}
ALLOWED_METADATA_KEYS = {"duration_ms", "source", "count", "detail", "package"}


def clean_metadata(raw):
    """Keep a small whitelist of scalar fields; drop everything else."""
    if not isinstance(raw, dict):
        return {}
    clean = {}
    for key in ALLOWED_METADATA_KEYS:
        value = raw.get(key)
        if isinstance(value, bool) or isinstance(value, (int, float)):
            clean[key] = value
        elif isinstance(value, str):
            clean[key] = value[:120]
    return clean


def record_violation(attempt, violation_type, metadata=None):
    """Record a violation on a locked, active attempt.

    Returns (violation, terminated). Terminates (with grading) when a counted
    violation reaches the exam's violation_limit and auto-submit is enabled.
    """
    severity, counted = VIOLATION_RULES[violation_type]
    violation = Violation.objects.create(
        attempt=attempt,
        violation_type=violation_type,
        severity=severity,
        metadata=metadata or {},
    )
    attempt.risk_score = F("risk_score") + severity
    fields = ["risk_score"]
    if counted:
        attempt.total_violations = F("total_violations") + 1
        fields.append("total_violations")
    attempt.save(update_fields=fields)
    attempt.refresh_from_db(fields=["risk_score", "total_violations"])

    exam = attempt.exam
    terminated = False
    if (
        counted
        and exam.auto_submit_on_violation
        and attempt.total_violations >= exam.violation_limit
    ):
        finalize_attempt(attempt, "terminated", REASON_VIOLATIONS)
        terminated = True
    return violation, terminated
