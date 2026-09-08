from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.http import HttpResponse
from django.db import transaction
from collections import defaultdict
from exams.models import Exam, ExamAttempt, Question
from monitoring.models import Violation
from django_ratelimit.decorators import ratelimit
from django.shortcuts import get_object_or_404
from core.permissions import IsOrgAdmin, IsOrgInvigilator
from datetime import timedelta
from django.utils.timezone import now
from exams.serializers import ExamSerializer, ExamDetailSerializer
from exams.views import _grade_saved_answers
from django.contrib.auth import get_user_model
from .report_export import generate_assessment_csv
from attempt_events.models import AttemptEvent
from attempt_events.services import record_attempt_event


User = get_user_model()


# ---------------- LIVE MONITOR ----------------

@api_view(['GET'])
@permission_classes([IsOrgInvigilator])
def live_monitor(request, exam_id):

    org = request.user.current_organisation

    exam = get_object_or_404(Exam, id=exam_id, organisation=org)

    data = []

    from django.db.models import OuterRef, Subquery

    latest_violation_qs = Violation.objects.filter(
        attempt=OuterRef('pk')
    ).order_by('-timestamp')

    attempts = (
        ExamAttempt.objects
        .filter(exam=exam)
        .select_related("user")
        .annotate(
            latest_violation_id=Subquery(latest_violation_qs.values('id')[:1]),
        )
        .order_by("user_id", "-start_time", "-id")
    )

    violation_ids = [a.latest_violation_id for a in attempts if a.latest_violation_id]
    violations_map = {v.id: v for v in Violation.objects.filter(id__in=violation_ids)}

    seen_users = set()
    current_time = now()
    HEARTBEAT_THRESHOLD = timedelta(seconds=60)

    for attempt in attempts:
        if attempt.user_id in seen_users:
            continue
        seen_users.add(attempt.user_id)

        deadline_has_passed = (
            attempt.deadline is not None and current_time >= attempt.deadline
        )
        is_online = (
            attempt.status == "active"
            and not deadline_has_passed
            and (current_time - attempt.last_active) < HEARTBEAT_THRESHOLD
        )

        display_status = "active" if is_online else "inactive"
        if attempt.status == 'terminated':
            display_status = 'terminated'

        latest_violation = violations_map.get(attempt.latest_violation_id) if attempt.latest_violation_id else None
        metadata = latest_violation.metadata if latest_violation and latest_violation.metadata else {}

        system_health = {
            "camera": metadata.get("camera", True),
            "tab_focus": metadata.get("tab", True),
            "fullscreen": metadata.get("fullscreen", True)
        }

        user = attempt.user
        full_name = f"{user.first_name} {user.last_name}".strip()
        display_name = full_name or user.name or user.username

        data.append({
            "username": user.username,
            "display_name": display_name,
            "attempt_id": attempt.id,
            "violations_count": attempt.total_violations,
            "risk_score": attempt.risk_score or 0,
            "status": display_status,
            "system_health": system_health,

            "latest_violation": {
                "type": latest_violation.violation_type,
                "severity": latest_violation.severity,
                "timestamp": latest_violation.timestamp
            } if latest_violation else None,

        })

    return Response(data)


# ---------------- USER DETAIL ----------------

@api_view(['GET'])
@permission_classes([IsOrgInvigilator])
def user_detail(request, username):
    return _user_detail_response(request, username=username)


@api_view(['GET'])
@permission_classes([IsOrgInvigilator])
def user_detail_exam(request, exam_id, username):
    return _user_detail_response(request, username=username, exam_id=exam_id)


def _user_detail_response(request, username, exam_id=None):

    org = request.user.current_organisation

    violations = Violation.objects.filter(
        attempt__user__username=username,
        attempt__exam__organisation=org
    )

    if exam_id:
        violations = violations.filter(attempt__exam_id=exam_id)

    breakdown = {}
    for v in violations:
        breakdown[v.violation_type] = breakdown.get(v.violation_type, 0) + 1

    return Response({
        "breakdown": breakdown,
    })


# ---------------- CLEAR VIOLATIONS ----------------

@ratelimit(key='user', rate='5/m', method='POST', block=True)
@api_view(['DELETE', 'POST'])
@permission_classes([IsOrgAdmin])
def clear_violations(request, username):

    org = request.user.current_organisation

    attempts = ExamAttempt.objects.filter(
        user__username=username,
        exam__organisation=org
    )

    Violation.objects.filter(attempt__in=attempts).delete()
    attempts.update(total_violations=0, risk_score=0)

    return Response({"status": "cleared"})


@ratelimit(key='user', rate='5/m', method='POST', block=True)
@ratelimit(key='user', rate='5/m', method='DELETE', block=True)
@api_view(['DELETE', 'POST'])
@permission_classes([IsOrgAdmin])
def clear_violations_exam(request, exam_id, username):

    org = request.user.current_organisation

    attempts = ExamAttempt.objects.filter(
        user__username=username,
        exam_id=exam_id,
        exam__organisation=org
    )

    Violation.objects.filter(attempt__in=attempts).delete()
    attempts.update(total_violations=0, risk_score=0)

    return Response({"status": "cleared"})


# ---------------- EXAMS ----------------

@api_view(['GET'])
@permission_classes([IsOrgAdmin])
def list_exams(request):

    org = request.user.current_organisation

    exams = Exam.objects.filter(organisation=org)

    serializer = ExamDetailSerializer(exams, many=True)
    return Response(serializer.data)


@ratelimit(key='user', rate='5/m', method='POST', block=True)
@api_view(['POST'])
@permission_classes([IsOrgAdmin])
def toggle_exam(request, exam_id):

    org = request.user.current_organisation

    with transaction.atomic():
        exam = get_object_or_404(
            Exam.objects.select_for_update(), id=exam_id, organisation=org
        )

        exam.is_active = not exam.is_active
        exam.save(update_fields=["is_active"])

        if not exam.is_active:
            questions = list(exam.questions.prefetch_related("options").all())
            active_attempts = ExamAttempt.objects.select_for_update().filter(
                exam=exam, status="active"
            )
            for attempt in active_attempts:
                score, total_points = _grade_saved_answers(attempt, exam, questions)
                ended_at = now()
                attempt.points_scored = score
                attempt.total_points = total_points
                attempt.status = "terminated"
                attempt.end_time = ended_at
                attempt.save(
                    update_fields=[
                        "points_scored",
                        "total_points",
                        "status",
                        "end_time",
                    ]
                )
                record_attempt_event(
                    attempt,
                    AttemptEvent.EventType.EXAM_TERMINATED,
                    metadata={"reason": "exam_deactivated"},
                )

    return Response({"status": "toggled"})


@api_view(['GET'])
@permission_classes([IsOrgAdmin])
def list_all_users(request):

    org = request.user.current_organisation

    users = User.objects.filter(
        memberships__organisation=org
    ).values('id', 'username', 'first_name', 'last_name')

    return Response(list(users))


# ---------------- UPDATE EXAM ----------------

@ratelimit(key='user', rate='3/m', method='PATCH', block=True)
@api_view(['PATCH'])
@permission_classes([IsOrgAdmin])
def update_exam(request, exam_id):

    org = request.user.current_organisation

    exam = get_object_or_404(Exam, id=exam_id, organisation=org)

    serializer = ExamSerializer(exam, data=request.data, partial=True, context={"request": request})
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "updated"})

    return Response(serializer.errors, status=400)

# ---------------- CREATE / DELETE ----------------

@ratelimit(key='user', rate='2/m', method='POST', block=True)
@api_view(['POST'])
@permission_classes([IsOrgAdmin])
def create_exam(request):

    serializer = ExamSerializer(data=request.data, context={"request":request})

    if serializer.is_valid():
        exam = serializer.save(
            created_by=request.user,
            organisation=request.user.current_organisation
        )

        return Response({
            "status": "created",
            "exam_id": exam.id
        })

    return Response(serializer.errors, status=400)


@ratelimit(key='user', rate='2/m', method='DELETE', block=True)
@api_view(['DELETE'])
@permission_classes([IsOrgAdmin])
def delete_exam(request, exam_id):

    org = request.user.current_organisation

    with transaction.atomic():
        exam = get_object_or_404(
            Exam.objects.select_for_update(), id=exam_id, organisation=org
        )
        if ExamAttempt.objects.filter(exam=exam).exists():
            return Response(
                {"error": "Cannot delete an exam that has attempt history."},
                status=400,
            )
        exam.delete()

    return Response({"status": "deleted"})


# ---------------- QA + RESULTS ----------------

@api_view(['GET'])
@permission_classes([IsOrgAdmin])
def exam_qa(request, exam_id):

    org = request.user.current_organisation

    questions = Question.objects.filter(
        exam_id=exam_id,
        exam__organisation=org
    )

    data = []
    for q in questions:
        data.append({
            "id": q.id,
            "text": q.text,
            "question_type": q.question_type,
            "points": q.points,
            "options": [
                {
                    "id": opt.id,
                    "text": opt.text,
                    "is_correct": opt.is_correct
                }
                for opt in q.options.all()
             ],
            "correct_text_answer": q.correct_text_answer
    })

    return Response(data)


@ratelimit(key='user', rate='10/m', method='GET', block=True)
@api_view(['GET'])
@permission_classes([IsOrgAdmin])
def exam_export_report(request, exam_id):

    org = request.user.current_organisation
    exam = get_object_or_404(Exam, id=exam_id, organisation=org)

    response = HttpResponse(
        generate_assessment_csv(exam),
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = 'attachment; filename="ParallaxLane_Assessment_Report.csv"'
    return response


@api_view(['GET'])
@permission_classes([IsOrgAdmin])
def exam_results(request, exam_id):

    org = request.user.current_organisation

    attempts = ExamAttempt.objects.filter(
        exam_id=exam_id,
        exam__organisation=org
    ).select_related('user').order_by('user__username', 'start_time', 'id')

    user_data = defaultdict(list)

    for a in attempts:
        user_data[a.user.username].append(a)

    data = []

    for username, attempts_list in user_data.items():
        latest = attempts_list[-1]

        data.append({
        "username": username,
        "attempts": len(attempts_list),
        "points_scored": latest.points_scored,
        "total_points": latest.total_points,
        "start_time": latest.start_time,
        "end_time": latest.end_time,
         })
    return Response(data)
