import random
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django_ratelimit.decorators import ratelimit
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from attempt_events.models import AttemptEvent
from attempt_events.services import record_attempt_event
from core.devices import HasApprovedDevice, verify_signature
from core.exceptions import api_error
from core.integrity import IntegrityUnavailable, request_hash_for, verify_integrity_token
from core.permissions import IsOrgMember
from organisations.models import OrganisationMember

from .models import Exam, ExamAttempt, Question
from .serializers import CandidateQuestionSerializer, ExamListSerializer
from .services import (
    REASON_DEADLINE,
    REASON_SUBMITTED,
    expire_if_due,
    finalize_attempt,
    save_answer,
)

# Backwards-compatible names for any external import.
from .services import grade_saved_answers as _grade_saved_answers  # noqa: F401
from .services import save_answer as _save_answer  # noqa: F401


def _exam_access_error(request):
    membership = OrganisationMember.objects.filter(
        organisation=request.user.current_organisation, user=request.user, is_active=True
    ).first()
    if not membership or not membership.is_exam_enabled:
        return api_error(
            "access_disabled", "Exam access disabled by organisation administrator.", 403
        )
    return None


def _attempt_payload(attempt, resumed):
    return {
        "attempt_id": attempt.id,
        "exam_id": attempt.exam_id,
        "resumed": resumed,
        "deadline": attempt.deadline,
        "server_time": now(),
        "state": attempt.status,
    }


def _expired_response(attempt):
    return api_error(
        "attempt_ended",
        "Exam attempt has ended",
        409,
        state=attempt.status,
        end_reason=attempt.end_reason,
        deadline=attempt.deadline,
        server_time=now(),
    )


def _challenge_key(user_id, exam_id):
    return f"start-challenge:{user_id}:{exam_id}"


def challenge_message(exam_id, nonce):
    """Exact string the app signs with its Keystore key (SHA256withECDSA)."""
    return f"parallaxlane-start:{exam_id}:{nonce}"


class ExamListView(generics.ListAPIView):
    permission_classes = [IsOrgMember]
    serializer_class = ExamListSerializer

    def get_queryset(self):
        org = self.request.user.current_organisation
        return Exam.objects.filter(organisation=org, is_published=True).order_by("start_time")


class ExamDetailView(generics.RetrieveAPIView):
    """Metadata always; questions only during the caller's own active attempt."""

    permission_classes = [IsOrgMember, HasApprovedDevice]

    def get_queryset(self):
        org = self.request.user.current_organisation
        return Exam.objects.filter(organisation=org, is_published=True)

    def retrieve(self, request, *args, **kwargs):
        exam = self.get_object()
        data = ExamListSerializer(exam).data
        data["server_time"] = now()

        with transaction.atomic():
            attempt = (
                ExamAttempt.objects.select_for_update()
                .filter(user=request.user, exam=exam, status="active")
                .first()
            )
            if attempt is not None and expire_if_due(attempt):
                attempt = None

        device = getattr(request, "exam_device", None)
        if (
            attempt is None
            or not exam.is_active
            or _exam_access_error(request) is not None
            or (device is not None and attempt.device_id and attempt.device_id != device.id)
        ):
            data["questions"] = None
            return Response(data)

        questions = list(exam.questions.prefetch_related("options").order_by("order", "id"))
        rng = random.Random(attempt.id)  # same order every time for this attempt
        rng.shuffle(questions)
        payload = CandidateQuestionSerializer(questions, many=True).data
        for question in payload:
            rng.shuffle(question["options"])

        data.update({
            "attempt_id": attempt.id,
            "deadline": attempt.deadline,
            "questions": payload,
        })
        return Response(data)


class StartChallengeView(generics.GenericAPIView):
    """Step 1 of start: a one-time nonce to sign and bind the integrity token to."""

    permission_classes = [IsOrgMember, HasApprovedDevice]

    @method_decorator(ratelimit(key="user", rate="10/m", method="POST", block=True))
    def post(self, request, pk):
        if not Exam.objects.filter(
            pk=pk, organisation=request.user.current_organisation, is_published=True
        ).exists():
            return api_error("exam_not_found", "Exam not found", 404)
        nonce = secrets.token_urlsafe(24)
        cache.set(
            _challenge_key(request.user.id, pk), nonce, settings.START_CHALLENGE_TTL_SECONDS
        )
        return Response({
            "nonce": nonce,
            "sign_payload": challenge_message(pk, nonce),
            "integrity_request_hash": request_hash_for(nonce),
            "expires_in": settings.START_CHALLENGE_TTL_SECONDS,
            "integrity_required": settings.INTEGRITY_REQUIRED,
        })


class StartExamView(generics.GenericAPIView):
    permission_classes = [IsOrgMember, HasApprovedDevice]

    @method_decorator(ratelimit(key="user", rate="10/m", method="POST", block=True))
    def post(self, request, pk):
        org = request.user.current_organisation
        access_error = _exam_access_error(request)
        if access_error:
            return access_error

        try:
            exam = Exam.objects.get(pk=pk, organisation=org, is_published=True)
        except Exam.DoesNotExist:
            return api_error("exam_not_found", "Exam not found", 404)
        if not exam.is_active:
            return api_error("exam_disabled", "Exam is disabled", 403)

        device = getattr(request, "exam_device", None)
        if device is not None:
            error = self._verify_challenge(request, exam, device)
            if error:
                return error

        with transaction.atomic():
            existing = (
                ExamAttempt.objects.select_for_update()
                .filter(user=request.user, exam=exam, status="active")
                .first()
            )
            if existing:
                return self._resume(existing, device)

            if ExamAttempt.objects.filter(
                user=request.user, exam=exam, status__in=["completed", "terminated"]
            ).exists():
                return api_error("already_attempted", "You have already attempted this exam", 409)

            current_time = now()
            if current_time < exam.start_time:
                return api_error("exam_not_started", "Exam has not started", 403,
                                 start_time=exam.start_time, server_time=current_time)
            if current_time > exam.end_time:
                return api_error("exam_window_closed", "Exam period has ended", 403)

            try:
                with transaction.atomic():  # savepoint: keep the outer txn usable
                    attempt = ExamAttempt.objects.create(
                        user=request.user,
                        exam=exam,
                        start_time=current_time,
                        last_active=current_time,
                        device=device,
                        deadline=min(
                            current_time + timedelta(minutes=exam.duration), exam.end_time
                        ),
                    )
            except IntegrityError:
                existing = (
                    ExamAttempt.objects.select_for_update()
                    .filter(user=request.user, exam=exam, status="active")
                    .first()
                )
                if existing:
                    return self._resume(existing, device)
                raise

        record_attempt_event(
            attempt,
            AttemptEvent.EventType.ATTEMPT_STARTED,
            metadata={"exam_id": exam.id, "device": device.device_id[:12] if device else None},
        )
        return Response(_attempt_payload(attempt, resumed=False))

    @staticmethod
    def _resume(attempt, device):
        attempt.ensure_deadline()
        if expire_if_due(attempt):
            return _expired_response(attempt)
        if device is not None and attempt.device_id and attempt.device_id != device.id:
            return api_error("device_mismatch", "Attempt was started on another device", 403)
        return Response(_attempt_payload(attempt, resumed=True))

    @staticmethod
    def _verify_challenge(request, exam, device):
        nonce = cache.get(_challenge_key(request.user.id, exam.id))
        cache.delete(_challenge_key(request.user.id, exam.id))  # single use
        if not nonce or request.data.get("nonce") != nonce:
            return api_error("challenge_invalid", "Start challenge missing or expired", 400)
        if not verify_signature(device, challenge_message(exam.id, nonce), request.data.get("signature")):
            return api_error("signature_invalid", "Device signature check failed", 403)
        if settings.INTEGRITY_REQUIRED:
            try:
                ok, reason = verify_integrity_token(request.data.get("integrity_token"), nonce)
            except IntegrityUnavailable:
                return api_error("integrity_unavailable",
                                 "Integrity check is temporarily unavailable. Retry.", 503)
            if not ok:
                return api_error("integrity_failed", "Device integrity check failed", 403,
                                 reason=reason)
        return None


class SaveAnswerView(generics.GenericAPIView):
    permission_classes = [IsOrgMember, HasApprovedDevice]

    @method_decorator(ratelimit(key="user", rate="120/m", method="POST", block=True))
    def post(self, request):
        user = request.user
        access_error = _exam_access_error(request)
        if access_error:
            return access_error

        try:
            attempt_id = int(request.data.get("attempt_id"))
            question_id = int(request.data.get("question_id"))
        except (TypeError, ValueError):
            return api_error("invalid_request", "attempt_id and question_id must be integers", 400)

        with transaction.atomic():
            try:
                attempt = ExamAttempt.objects.select_for_update().select_related("exam").get(
                    id=attempt_id, user=user, exam__organisation=user.current_organisation
                )
            except ExamAttempt.DoesNotExist:
                return api_error("attempt_not_found", "Invalid attempt", 404)

            device = getattr(request, "exam_device", None)
            if device is not None and attempt.device_id and attempt.device_id != device.id:
                return api_error("device_mismatch", "Attempt belongs to another device", 403)

            try:
                question = Question.objects.get(id=question_id, exam=attempt.exam)
            except Question.DoesNotExist:
                return api_error("invalid_question", "Question does not belong to this exam", 400)

            if attempt.status != "active":
                return _expired_response(attempt)
            if expire_if_due(attempt):
                return _expired_response(attempt)
            if not attempt.exam.is_active:
                return api_error("exam_disabled", "Exam is disabled", 403)

            if "answer" not in request.data:
                return api_error("invalid_request", "answer is required", 400)
            try:
                answer, created, changed = save_answer(
                    attempt, question, request.data.get("answer"), strict=True
                )
            except ValueError as exc:
                return api_error("invalid_answer", str(exc), 400)

        if created or changed:
            record_attempt_event(
                attempt,
                AttemptEvent.EventType.ANSWER_SAVED if created else AttemptEvent.EventType.ANSWER_CHANGED,
                question=question,
                metadata={"question_type": question.question_type, "replaced_existing": not created},
            )

        return Response({
            "status": "saved",
            "attempt_id": attempt.id,
            "question_id": question.id,
            "answer_id": answer.id,
            "updated": not created,
            "server_time": now(),
        })


class SubmitExamView(generics.GenericAPIView):
    permission_classes = [IsOrgMember, HasApprovedDevice]

    @method_decorator(ratelimit(key="user", rate="5/m", method="POST", block=True))
    def post(self, request, pk):
        user = request.user
        access_error = _exam_access_error(request)
        if access_error:
            return access_error

        answers = request.data.get("answers", {})
        if not isinstance(answers, dict):
            return api_error("invalid_request", "answers must be an object", 400)

        with transaction.atomic():
            attempt = (
                ExamAttempt.objects.select_for_update()
                .select_related("exam")
                .filter(user=user, exam_id=pk, exam__organisation=user.current_organisation)
                .order_by("-start_time")
                .first()
            )
            if not attempt:
                return api_error("attempt_not_found", "No exam attempt found", 404)

            device = getattr(request, "exam_device", None)
            if device is not None and attempt.device_id and attempt.device_id != device.id:
                return api_error("device_mismatch", "Attempt belongs to another device", 403)

            if attempt.status != "active":
                # Idempotent: a retried submit after success returns the result.
                if attempt.status == "completed":
                    return Response(self._result(attempt, "Exam already submitted"))
                return _expired_response(attempt)

            exam = attempt.exam
            questions = {q.id: q for q in exam.questions.prefetch_related("options")}
            if len(answers) > len(questions):
                return api_error("invalid_request",
                                 f"Too many answers submitted (max {len(questions)})", 400)

            current_time = now()
            attempt.ensure_deadline()
            within_grace = current_time <= attempt.deadline + timedelta(
                seconds=settings.SUBMIT_GRACE_SECONDS
            )
            if within_grace:
                for raw_id, value in answers.items():
                    try:
                        question = questions.get(int(raw_id))
                    except (TypeError, ValueError):
                        question = None
                    if question:
                        save_answer(attempt, question, value, strict=False)
                reason = REASON_SUBMITTED
            else:
                reason = REASON_DEADLINE  # too late: grade only what was saved in time

            finalize_attempt(attempt, "completed", reason, at_time=current_time)

        return Response(self._result(attempt, "Exam submitted successfully"))

    @staticmethod
    def _result(attempt, message):
        return {
            "message": message,
            "state": attempt.status,
            "end_reason": attempt.end_reason,
            "points_scored": attempt.points_scored,
            "total_points": attempt.total_points,
            "total_questions": attempt.exam.questions.count(),
        }


@api_view(["GET"])
@permission_classes([IsOrgMember])
def my_results(request):
    org = request.user.current_organisation
    attempts = (
        ExamAttempt.objects.filter(
            user=request.user, exam__organisation=org, status__in=["completed", "terminated"]
        )
        .select_related("exam")
        .prefetch_related("exam__questions")
        .order_by("-start_time")
    )
    return Response([
        {
            "attempt_id": attempt.id,
            "exam_id": attempt.exam_id,
            "exam_title": attempt.exam.title,
            "points_scored": attempt.points_scored or 0,
            "total_points": attempt.total_points or 0,
            "total_questions": len(attempt.exam.questions.all()),
            "violations": attempt.total_violations,
            "status": attempt.status.capitalize(),
            "state": attempt.status,
            "end_reason": attempt.end_reason,
            "date": attempt.start_time,
        }
        for attempt in attempts
    ])
