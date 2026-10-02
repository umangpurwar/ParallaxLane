import secrets

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django_ratelimit.decorators import ratelimit
from rest_framework.response import Response
from rest_framework.views import APIView

from attempt_events.models import AttemptEvent
from attempt_events.services import record_attempt_event
from core.devices import HasApprovedDevice
from core.exceptions import api_error
from core.integrity import IntegrityUnavailable, verify_integrity_token
from core.permissions import IsOrgMember
from core.validators import parse_attempt_id
from exams.models import ExamAttempt, Question
from exams.services import expire_if_due

from .services import CLIENT_REPORTABLE, clean_metadata, record_violation

CLIENT_EVENT_TYPES = {
    AttemptEvent.EventType.QUESTION_VIEWED,
    AttemptEvent.EventType.QUESTION_SKIPPED,
    AttemptEvent.EventType.QUESTION_NAVIGATION,
    AttemptEvent.EventType.APP_BACKGROUNDED,
    AttemptEvent.EventType.APP_RESUMED,
    AttemptEvent.EventType.NETWORK_OFFLINE,
    AttemptEvent.EventType.NETWORK_RESTORED,
}
MAX_EVENTS_PER_BATCH = 50
CLIENT_STATE_KEYS = {"foreground", "lock_task", "multi_window", "overlay_suspect"}


def _attempt_state(attempt):
    return {
        "state": attempt.status,
        "end_reason": attempt.end_reason,
        "deadline": attempt.deadline,
        "server_time": now(),
        "violations": attempt.total_violations,
        "risk": attempt.risk_score,
    }


def _ended_response(attempt):
    code = "attempt_terminated" if attempt.status == "terminated" else "attempt_ended"
    return api_error(code, "Exam attempt has ended", 409, **_attempt_state(attempt))


def _resolve_active_attempt(request, raw_attempt_id):
    """Lock and return an owned, active, unexpired attempt in the current org.

    Must be called inside transaction.atomic(). Returns (attempt, error_response).
    """
    try:
        attempt_id = parse_attempt_id(raw_attempt_id)
    except ValueError as exc:
        return None, api_error("invalid_request", str(exc), 400)

    try:
        attempt = ExamAttempt.objects.select_for_update().select_related("exam").get(
            id=attempt_id,
            user=request.user,
            exam__organisation=request.user.current_organisation,
        )
    except ExamAttempt.DoesNotExist:
        return None, api_error("attempt_not_found", "Invalid attempt", 404)

    device = getattr(request, "exam_device", None)
    if device is not None and attempt.device_id and attempt.device_id != device.id:
        return None, api_error("device_mismatch", "Attempt belongs to another device", 403)

    if attempt.status != "active":
        return None, _ended_response(attempt)
    if expire_if_due(attempt):
        return None, _ended_response(attempt)
    if not attempt.exam.is_active:
        return None, api_error("exam_disabled", "Exam is disabled", 403)
    return attempt, None


def _integrity_nonce_key(attempt_id):
    return f"hb-integrity-nonce:{attempt_id}"


def _current_integrity_nonce(attempt_id):
    key = _integrity_nonce_key(attempt_id)
    nonce = cache.get(key)
    if not nonce:
        nonce = secrets.token_urlsafe(24)
        cache.set(key, nonce, 6 * 60 * 60)
    return nonce


class LogViolationView(APIView):
    permission_classes = [IsOrgMember, HasApprovedDevice]

    @method_decorator(ratelimit(key="user", rate="20/m", method="POST", block=True))
    def post(self, request):
        violation_type = request.data.get("type")
        if violation_type not in CLIENT_REPORTABLE:
            return api_error("invalid_violation_type", "Invalid violation type", 400)
        metadata = request.data.get("metadata") or {}
        if not isinstance(metadata, dict):
            return api_error("invalid_request", "metadata must be an object", 400)

        with transaction.atomic():
            attempt, error = _resolve_active_attempt(request, request.data.get("attempt_id"))
            if error:
                return error
            _, terminated = record_violation(attempt, violation_type, clean_metadata(metadata))

        body = {"status": "logged", **_attempt_state(attempt)}
        if terminated:
            body["code"] = "attempt_terminated"
        return Response(body)


class HeartbeatView(APIView):
    """Liveness + client state. Silence is detected server-side as a gap."""

    permission_classes = [IsOrgMember, HasApprovedDevice]

    @method_decorator(ratelimit(key="user", rate="30/m", method="POST", block=True))
    def post(self, request):
        client_state = request.data.get("state") or {}
        if not isinstance(client_state, dict):
            return api_error("invalid_request", "state must be an object", 400)
        integrity_token = request.data.get("integrity_token")

        with transaction.atomic():
            attempt, error = _resolve_active_attempt(request, request.data.get("attempt_id"))
            if error:
                return error

            current_time = now()
            gap = (current_time - attempt.last_active).total_seconds()
            if gap > settings.HEARTBEAT_GAP_SECONDS:
                _, terminated = record_violation(
                    attempt, "heartbeat_gap", {"detail": f"{int(gap)}s without heartbeat"}
                )
                if terminated:
                    return _ended_response(attempt)

            if integrity_token:
                nonce = _current_integrity_nonce(attempt.id)
                try:
                    ok, reason = verify_integrity_token(integrity_token, nonce)
                except IntegrityUnavailable:
                    ok, reason = True, "unavailable"  # Google down: don't punish
                cache.delete(_integrity_nonce_key(attempt.id))  # one token per nonce
                if not ok:
                    _, terminated = record_violation(attempt, "integrity_failed", {"detail": reason})
                    if terminated:
                        return _ended_response(attempt)

            attempt.last_active = current_time
            attempt.last_client_state = {
                key: bool(client_state.get(key))
                for key in CLIENT_STATE_KEYS
                if key in client_state
            }
            attempt.save(update_fields=["last_active", "last_client_state"])

        return Response({
            "status": "alive",
            **_attempt_state(attempt),
            "integrity_nonce": _current_integrity_nonce(attempt.id),
        })


class AttemptEventsView(APIView):
    """Batched client telemetry for the attempt timeline (not violations)."""

    permission_classes = [IsOrgMember, HasApprovedDevice]

    @method_decorator(ratelimit(key="user", rate="30/m", method="POST", block=True))
    def post(self, request):
        events = request.data.get("events")
        if not isinstance(events, list) or not events:
            return api_error("invalid_request", "events must be a non-empty list", 400)
        if len(events) > MAX_EVENTS_PER_BATCH:
            return api_error(
                "invalid_request", f"At most {MAX_EVENTS_PER_BATCH} events per batch", 400
            )

        with transaction.atomic():
            attempt, error = _resolve_active_attempt(request, request.data.get("attempt_id"))
            if error:
                return error
            question_ids = set(
                Question.objects.filter(exam=attempt.exam).values_list("id", flat=True)
            )

        accepted = 0
        for item in events:
            if not isinstance(item, dict) or item.get("type") not in CLIENT_EVENT_TYPES:
                continue
            question = None
            qid = item.get("question_id")
            if isinstance(qid, int) and qid in question_ids:
                question = Question(id=qid)
            metadata = clean_metadata(item.get("metadata"))
            client_ts = item.get("client_ts")
            if isinstance(client_ts, int):
                metadata["client_ts"] = client_ts
            if record_attempt_event(attempt, item["type"], question=question, metadata=metadata):
                accepted += 1

        return Response({"accepted": accepted, "server_time": now()})
