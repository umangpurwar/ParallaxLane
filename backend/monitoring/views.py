from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.timezone import now
from rest_framework.decorators import api_view, permission_classes
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.db.models import F
from django.db import transaction

from core.permissions import IsOrgMember
from core.validators import parse_attempt_id
from .models import Violation
from exams.models import ExamAttempt
from attempt_events.models import AttemptEvent
from attempt_events.services import record_attempt_event

VIOLATION_SEVERITY_MAP = {
    "tab_switch": 3,
    "window_blur": 4,
    "copy_paste": 5,
}

def _resolve_attempt_id(request):
    try:
        return parse_attempt_id(request.data.get("attempt_id")), None
    except ValueError as exc:
        return None, str(exc)


def _resolve_active_attempt(request, attempt_id):
    """Resolve an owned, current-organisation attempt using server time."""
    org = request.user.current_organisation
    try:
        attempt = ExamAttempt.objects.select_for_update().select_related("exam").get(
            id=attempt_id,
            user=request.user,
            exam__organisation=org,
        )
    except ExamAttempt.DoesNotExist:
        return None, Response({"error": "Invalid attempt"}, status=400)

    if attempt.status != "active":
        return None, Response({"error": "Exam already ended"}, status=400)

    current_time = now()
    if attempt.is_expired(current_time):
        attempt.status = "terminated"
        attempt.end_time = current_time
        attempt.save(update_fields=["status", "end_time"])
        record_attempt_event(
            attempt,
            AttemptEvent.EventType.EXAM_TERMINATED,
            metadata={"reason": "deadline_expired"},
        )
        return None, Response(
            {"error": "Exam attempt has expired", "deadline": attempt.deadline},
            status=400,
        )

    if not attempt.exam.is_active:
        return None, Response({"error": "Exam is disabled"}, status=403)
    return attempt, None


class LogViolationView(APIView):
    permission_classes = [IsOrgMember]

    @method_decorator(ratelimit(key='user', rate='10/m', method='POST', block=True))
    def post(self, request):
        attempt_id, err = _resolve_attempt_id(request)
        if err:
            return Response({"error": err}, status=400)

        violation_type = request.data.get("type")
        metadata = request.data.get("metadata", {})

        if not violation_type:
            return Response({"error": "type is required"}, status=400)
        if violation_type not in VIOLATION_SEVERITY_MAP:
            return Response({"error": "Invalid violation type"}, status=400)
        if metadata is not None and not isinstance(metadata, dict):
            return Response({"error": "metadata must be an object"}, status=400)

        severity = min(VIOLATION_SEVERITY_MAP.get(violation_type, 1), 10)
        with transaction.atomic():
            attempt, error = _resolve_active_attempt(request, attempt_id)
            if error:
                return error

            Violation.objects.create(attempt=attempt, violation_type=violation_type, severity=severity, metadata=metadata or {})

            ExamAttempt.objects.filter(id=attempt.id).update(
                total_violations=F('total_violations') + 1,
                risk_score=F('risk_score') + severity
            )

            attempt.refresh_from_db()
            exam = attempt.exam
            if exam.auto_submit_on_violation and attempt.total_violations >= exam.violation_limit:
                attempt.status = "terminated"
                attempt.end_time = now()
                attempt.save()
                record_attempt_event(
                    attempt,
                    AttemptEvent.EventType.EXAM_TERMINATED,
                    metadata={
                        "reason": "violation_threshold",
                        "total_violations": attempt.total_violations,
                    },
                )

        return Response({
            "status": "logged",
            "violations": attempt.total_violations,
            "risk": attempt.risk_score,
            "state": attempt.status
        })


@ratelimit(key='user', rate='30/m', method='POST', block=True)
@api_view(['POST'])
@permission_classes([IsOrgMember])
def student_heartbeat(request):
    attempt_id, err = _resolve_attempt_id(request)
    if err:
        return Response({"error": err}, status=400)

    with transaction.atomic():
        attempt, error = _resolve_active_attempt(request, attempt_id)
        if error:
            return error
        attempt.last_active = now()
        attempt.save(update_fields=["last_active"])

    return Response({"status": "alive"})
