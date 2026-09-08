from datetime import timedelta

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db import transaction, IntegrityError
from django.db.models import Prefetch
from .models import Question, Answer, ExamAttempt, Exam, QuestionOption
from django.utils.timezone import now
from core.permissions import IsOrgMember
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .serializers import ExamListSerializer
from .serializers import ExamDetailSerializer
from monitoring.models import Violation
from attempt_events.models import AttemptEvent
from attempt_events.services import record_attempt_event


def _save_answer(attempt, question, value, strict=True):
    """Create or update one answer, validating it against its question."""
    defaults = {
        "selected_option": None,
        "text_answer": None,
        "file_upload": None,
        "is_correct": None,
    }

    if question.question_type in ["mcq", "true_false"]:
        if isinstance(value, bool):
            option_id = None
        else:
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
            value = str(value)
        defaults["text_answer"] = value
    elif question.question_type in ["file_upload", "image_based"]:
        # The existing backend stores these as an answer placeholder. File
        # upload handling remains outside this task.
        pass

    existing = Answer.objects.filter(attempt=attempt, question=question).first()
    changed = False
    if existing:
        changed = (
            existing.selected_option_id != getattr(defaults["selected_option"], "id", None)
            or existing.text_answer != defaults["text_answer"]
            or bool(existing.file_upload) != bool(defaults["file_upload"])
        )

    answer, created = Answer.objects.update_or_create(
        attempt=attempt,
        question=question,
        defaults=defaults,
    )
    return answer, created, changed


def _grade_saved_answers(attempt, exam, questions):
    """Recalculate grading from persisted answers at final submission time."""
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


def _terminate_expired_attempt(attempt, at_time):
    """Transition an active attempt to terminated exactly once at expiry."""
    attempt.status = "terminated"
    attempt.end_time = at_time
    attempt.save(update_fields=["status", "end_time"])
    record_attempt_event(
        attempt,
        AttemptEvent.EventType.EXAM_TERMINATED,
        metadata={"reason": "deadline_expired"},
    )


class ExamListView(generics.ListAPIView):
    serializer_class = ExamListSerializer
    permission_classes = [IsOrgMember]

    def get_queryset(self):
        org = self.request.user.current_organisation
        return Exam.objects.filter(organisation=org, is_published=True)


class ExamDetailView(generics.RetrieveAPIView):
    serializer_class = ExamDetailSerializer
    permission_classes = [IsOrgMember]

    def get_queryset(self):
        org = self.request.user.current_organisation
        return Exam.objects.filter(organisation=org, is_published=True).prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.order_by("order").prefetch_related("options"),
            )
        )


class StartExamView(generics.GenericAPIView):
    permission_classes = [IsOrgMember]

    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def post(self, request, pk):
        org = request.user.current_organisation
        
        from organisations.models import OrganisationMember
        membership = OrganisationMember.objects.filter(organisation=org, user=request.user).first()
        
        if not membership or not membership.is_exam_enabled:
            return Response({"error": "Exam access disabled by organisation administrator."}, status=403)

        with transaction.atomic():
            try:
                exam = Exam.objects.select_for_update().get(pk=pk, organisation=org)
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found"}, status=404)

            if not exam.is_active:
                return Response({"error": "Exam is disabled"}, status=403)

            if now() > exam.end_time:
                return Response({"error": "Exam period has ended"}, status=403)

            existing = ExamAttempt.objects.filter(
                user=request.user, exam=exam, status="active"
            ).first()

            if existing:
                existing.ensure_deadline()
                current_time = now()
                if existing.is_expired(current_time):
                    _terminate_expired_attempt(existing, current_time)
                    return Response(
                        {
                            "error": "Exam attempt has expired",
                            "deadline": existing.deadline,
                        },
                        status=400,
                    )
                return Response({
                    "attempt_id": existing.id,
                    "exam_id": exam.id,
                    "resumed": True,
                    "deadline": existing.deadline,
                })

            already_done = ExamAttempt.objects.filter(
                user=request.user, exam=exam, status__in=["completed", "terminated"]
            ).exists()

            if already_done:
                return Response({"error": "You have already attempted this exam"}, status=400)

            if now() < exam.start_time:
                return Response({"error": "Exam has not started"}, status=403)

            try:
                started_at = now()
                attempt = ExamAttempt.objects.create(
                    user=request.user,
                    exam=exam,
                    start_time=started_at,
                    deadline=min(
                        started_at + timedelta(minutes=exam.duration),
                        exam.end_time,
                    ),
                )
            except IntegrityError:
                existing = ExamAttempt.objects.filter(
                    user=request.user, exam=exam, status="active"
                ).first()
                if existing:
                    existing.ensure_deadline()
                    current_time = now()
                    if existing.is_expired(current_time):
                        _terminate_expired_attempt(existing, current_time)
                        return Response(
                            {
                                "error": "Exam attempt has expired",
                                "deadline": existing.deadline,
                            },
                            status=400,
                        )
                    return Response({
                        "attempt_id": existing.id,
                        "exam_id": exam.id,
                        "resumed": True,
                        "deadline": existing.deadline,
                    })
                raise

        record_attempt_event(
            attempt,
            AttemptEvent.EventType.ATTEMPT_STARTED,
            metadata={"exam_id": exam.id},
        )

        return Response({
            "attempt_id": attempt.id,
            "exam_id": exam.id,
            "resumed": False,
            "deadline": attempt.deadline,
        })


class SaveAnswerView(generics.GenericAPIView):
    permission_classes = [IsOrgMember]

    @method_decorator(ratelimit(key='user', rate='120/m', method='POST', block=True))
    def post(self, request):
        user = request.user
        org = user.current_organisation

        from organisations.models import OrganisationMember
        membership = OrganisationMember.objects.filter(
            organisation=org, user=user
        ).first()
        if not membership or not membership.is_exam_enabled:
            return Response(
                {"error": "Exam access disabled by organisation administrator."},
                status=403,
            )

        try:
            attempt_id = int(request.data.get("attempt_id"))
            question_id = int(request.data.get("question_id"))
        except (TypeError, ValueError):
            return Response(
                {"error": "attempt_id and question_id must be integers"},
                status=400,
            )

        with transaction.atomic():
            try:
                attempt = ExamAttempt.objects.select_for_update().select_related(
                    "exam"
                ).get(id=attempt_id, user=user)
            except ExamAttempt.DoesNotExist:
                return Response({"error": "Invalid attempt"}, status=404)

            try:
                question = Question.objects.get(id=question_id)
            except Question.DoesNotExist:
                return Response({"error": "Invalid question"}, status=400)

            exam = attempt.exam
            if question.exam_id != exam.id:
                return Response(
                    {"error": "Question does not belong to this exam"}, status=400
                )
            if exam.organisation_id != org.id:
                return Response({"error": "Invalid attempt"}, status=404)
            if not exam.is_active:
                return Response({"error": "Exam is disabled"}, status=403)
            if attempt.status != "active":
                return Response({"error": "Exam already ended"}, status=400)

            current_time = now()
            if attempt.is_expired(current_time):
                _terminate_expired_attempt(attempt, current_time)
                return Response(
                    {
                        "error": "Exam attempt has expired",
                        "deadline": attempt.deadline,
                    },
                    status=400,
                )

            if "answer" not in request.data and question.question_type not in [
                "file_upload", "image_based"
            ]:
                return Response({"error": "answer is required"}, status=400)

            try:
                answer, created, changed = _save_answer(
                    attempt, question, request.data.get("answer"), strict=True
                )
            except ValueError as exc:
                return Response({"error": str(exc)}, status=400)

        if created:
            record_attempt_event(
                attempt,
                AttemptEvent.EventType.ANSWER_SAVED,
                question=question,
                metadata={
                    "question_type": question.question_type,
                    "replaced_existing": False,
                },
            )
        elif changed:
            record_attempt_event(
                attempt,
                AttemptEvent.EventType.ANSWER_CHANGED,
                question=question,
                metadata={
                    "question_type": question.question_type,
                    "replaced_existing": True,
                },
            )

        return Response(
            {
                "status": "saved",
                "attempt_id": attempt.id,
                "question_id": question.id,
                "answer_id": answer.id,
                "updated": not created,
            }
        )


class SubmitExamView(generics.GenericAPIView):
    permission_classes = [IsOrgMember]

    @method_decorator(ratelimit(key='user', rate='3/m', method='POST', block=True))
    def post(self, request, pk):
        user = request.user
        org = user.current_organisation
        
        from organisations.models import OrganisationMember
        membership = OrganisationMember.objects.filter(organisation=org, user=user).first()
        
        if not membership or not membership.is_exam_enabled:
            return Response({"error": "Exam access disabled by organisation administrator."}, status=403)

        with transaction.atomic():
            try:
                exam = Exam.objects.select_for_update().get(pk=pk, organisation=org)
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found"}, status=404)

            attempt = ExamAttempt.objects.select_for_update().filter(
                user=user, exam=exam, status="active"
            ).first()

            if not attempt:
                return Response({"error": "No active exam attempt found"}, status=400)

            if attempt.status == "terminated":
                return Response({"error": "Exam has been terminated"}, status=403)

            if attempt.status == "completed":
                return Response({"error": "Exam already submitted"}, status=400)

            current_time = now()
            if attempt.is_expired(current_time):
                _terminate_expired_attempt(attempt, current_time)
                return Response(
                    {
                        "error": "Exam attempt has expired",
                        "deadline": attempt.deadline,
                    },
                    status=400,
                )

            answers = request.data.get("answers", {})
            if not isinstance(answers, dict):
                return Response({"error": "answers must be an object"}, status=400)

            questions = list(
                exam.questions.prefetch_related("options").all()
            )
            question_count = len(questions)
            if len(answers) > question_count:
                return Response(
                    {"error": f"Too many answers submitted (max {question_count})"},
                    status=400,
                )

            questions_by_id = {q.id: q for q in questions}
            total_points = sum(q.points for q in questions)

            for question_id_raw, submitted_answer in answers.items():
                try:
                    question_id = int(question_id_raw)
                except (TypeError, ValueError):
                    continue

                question = questions_by_id.get(question_id)
                if not question:
                    continue

                _save_answer(attempt, question, submitted_answer, strict=False)

            score, total_points = _grade_saved_answers(attempt, exam, questions)
            attempt.points_scored = score
            attempt.total_points = total_points
            attempt.status = "completed"
            attempt.end_time = now()
            attempt.save()

        record_attempt_event(
            attempt,
            AttemptEvent.EventType.EXAM_SUBMITTED,
            metadata={
                "total_questions": question_count,
                "points_scored": score,
            },
        )

        return Response({
            "message": "Exam submitted successfully",
            "points_scored": score,
            "total_points": total_points,
            "total_questions": question_count,
        })


@api_view(['GET'])
@permission_classes([IsOrgMember])
def my_results(request):
    org = request.user.current_organisation
    attempts = ExamAttempt.objects.filter(
        user=request.user,
        exam__organisation=org,
        status__in=['completed', 'terminated']
    ).select_related('exam').prefetch_related('exam__questions')

    data = []
    for attempt in attempts:
        data.append({
            "attempt_id": attempt.id,
            "exam_title": attempt.exam.title,
            "points_scored": attempt.points_scored or 0,
            "total_points": attempt.total_points or 0,
            "total_questions": attempt.exam.questions.count(),
            "violations": attempt.total_violations,
            "status": attempt.status.capitalize(),
            "date": attempt.start_time
        })

    return Response(data)


