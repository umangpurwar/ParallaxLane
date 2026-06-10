from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.timezone import now
from rest_framework.decorators import api_view, permission_classes
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.db.models import F
import logging

from core.permissions import IsOrgMember
from .models import Violation, Screenshot
from exams.models import ExamAttempt

logger = logging.getLogger(__name__)

VIOLATION_SEVERITY_MAP = {
    "tab_switch": 3,
    "multiple_faces": 8,
    "no_face": 6,
    "phone_detected": 9,
    "window_blur": 4,
    "copy_paste": 5,
    "suspicious_movement": 2,
}


class LogViolationView(APIView):
    permission_classes = [IsOrgMember]

    @method_decorator(ratelimit(key='user', rate='10/m', method='POST', block=True))
    def post(self, request):
        attempt_id = request.data.get("attempt_id")
        violation_type = request.data.get("type")
        metadata = request.data.get("metadata", {})

        if not attempt_id:
            return Response({"error": "attempt_id is required"}, status=400)
        if not violation_type:
            return Response({"error": "type is required"}, status=400)
        if violation_type not in VIOLATION_SEVERITY_MAP:
            return Response({"error": "Invalid violation type"}, status=400)

        severity = min(VIOLATION_SEVERITY_MAP.get(violation_type, 1), 10)
        org = request.user.current_organisation

        try:
            attempt = ExamAttempt.objects.get(id=attempt_id, user=request.user, exam__organisation=org)
        except ExamAttempt.DoesNotExist:
            return Response({"error": "Invalid attempt"}, status=400)

        if attempt.status != "active":
            return Response({"error": "Exam already ended"}, status=400)

        Violation.objects.create(attempt=attempt, violation_type=violation_type, severity=severity, metadata=metadata)

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

        return Response({
            "status": "logged",
            "violations": attempt.total_violations,
            "risk": attempt.risk_score,
            "state": attempt.status
        })


class ScreenshotUploadView(APIView):
    permission_classes = [IsOrgMember]

    @method_decorator(ratelimit(key='user', rate='2/m', method='POST', block=True))
    def post(self, request):
        attempt_id = request.data.get("attempt_id")
        image_file = request.FILES.get("image")

        if not attempt_id:
            return Response({"error": "attempt_id is required"}, status=400)
        if not image_file:
            return Response({"error": "image file is required"}, status=400)

        org = request.user.current_organisation

        try:
            attempt = ExamAttempt.objects.get(id=attempt_id, user=request.user, exam__organisation=org)
        except ExamAttempt.DoesNotExist:
            return Response({"error": "Invalid attempt"}, status=400)

        if attempt.status != "active":
            return Response({"error": "Exam already ended"}, status=400)

        # FIX: guard cloudinary import inside the function
        try:
            import cloudinary.uploader
            upload_result = cloudinary.uploader.upload(image_file, folder="screenshots")
            image_url = upload_result.get("secure_url")
        except Exception as e:
            logger.error(f"Screenshot upload failed: {e}")
            return Response({"error": "Upload failed"}, status=500)

        Screenshot.objects.create(attempt=attempt, image=image_url)
        return Response({"status": "saved", "url": image_url})


@ratelimit(key='user', rate='30/m', method='POST', block=True)
@api_view(['POST'])
@permission_classes([IsOrgMember])
def student_heartbeat(request):
    attempt_id = request.data.get("attempt_id")

    if not attempt_id:
        return Response({"error": "attempt_id required"}, status=400)

    org = request.user.current_organisation
    updated = ExamAttempt.objects.filter(
        id=attempt_id, user=request.user, exam__organisation=org
    ).update(last_active=now())

    if not updated:
        return Response({"error": "Invalid attempt"}, status=400)

    return Response({"status": "alive"})