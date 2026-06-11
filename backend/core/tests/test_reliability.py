from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils.timezone import now
from rest_framework.test import APIClient

from exams.models import Exam, ExamAttempt, Question, QuestionOption
from organisations.models import Organisation, OrganisationMember

User = get_user_model()


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    RATELIMIT_ENABLE=False,
)
class ReliabilityTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="TestPass1!",
            name="Admin",
        )
        self.candidate = User.objects.create_user(
            username="candidate@test.com",
            email="candidate@test.com",
            password="TestPass1!",
            name="Candidate",
        )
        self.org = Organisation.objects.create(name="Rel Org", slug="rel-org", owner=self.admin)
        OrganisationMember.objects.create(organisation=self.org, user=self.admin, role="owner")
        OrganisationMember.objects.create(organisation=self.org, user=self.candidate, role="candidate")
        self.admin.current_organisation = self.org
        self.admin.save()
        self.candidate.current_organisation = self.org
        self.candidate.save()

        start = now()
        self.exam = Exam.objects.create(
            title="Rel Exam",
            description="",
            duration=30,
            start_time=start,
            end_time=start + timedelta(days=1),
            created_by=self.admin,
            organisation=self.org,
            is_active=True,
        )
        self.question = Question.objects.create(
            exam=self.exam, text="Q1", question_type="mcq", points=1
        )
        self.correct = QuestionOption.objects.create(
            question=self.question, text="A", is_correct=True
        )
        QuestionOption.objects.create(question=self.question, text="B", is_correct=False)

    def _login(self, email):
        res = self.client.post(
            "/api/login/",
            {"email": email, "password": "TestPass1!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def test_start_exam_unique_active_constraint(self):
        ExamAttempt.objects.create(user=self.candidate, exam=self.exam, status="active")
        with self.assertRaises(IntegrityError):
            ExamAttempt.objects.create(user=self.candidate, exam=self.exam, status="active")

    def test_start_exam_resumes_on_duplicate_request(self):
        self._login("candidate@test.com")
        r1 = self.client.post(f"/api/exams/{self.exam.id}/start/", format="json")
        r2 = self.client.post(f"/api/exams/{self.exam.id}/start/", format="json")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.data["attempt_id"], r2.data["attempt_id"])
        self.assertTrue(r2.data.get("resumed"))
        self.assertEqual(
            ExamAttempt.objects.filter(user=self.candidate, exam=self.exam, status="active").count(),
            1,
        )

    def test_submit_rejects_oversized_answers_payload(self):
        self._login("candidate@test.com")
        start = self.client.post(f"/api/exams/{self.exam.id}/start/", format="json")
        attempt_id = start.data["attempt_id"]

        huge = {str(i): self.correct.id for i in range(100)}
        res = self.client.post(
            f"/api/exams/{self.exam.id}/submit/",
            {"answers": huge},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Too many answers", res.data["error"])

    def test_submit_rejects_non_object_answers(self):
        self._login("candidate@test.com")
        self.client.post(f"/api/exams/{self.exam.id}/start/", format="json")
        res = self.client.post(
            f"/api/exams/{self.exam.id}/submit/",
            {"answers": ["bad"]},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_send_otp_rejects_invalid_email(self):
        res = self.client.post(
            "/api/accounts/send-otp/",
            {"email": "not-an-email", "mode": "register"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid email", res.data["error"])

    def test_invite_rejects_invalid_email(self):
        self._login("admin@test.com")
        res = self.client.post(
            f"/api/organisations/{self.org.slug}/invite/",
            {"email": "bad@", "role": "candidate"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_create_org_rejects_empty_name(self):
        self._login("admin@test.com")
        res = self.client.post(
            "/api/organisations/create/",
            {"name": "   "},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_log_violation_rejects_non_numeric_attempt_id(self):
        self._login("candidate@test.com")
        res = self.client.post(
            "/api/monitoring/log/",
            {"attempt_id": "abc", "type": "tab_switch"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid attempt_id", res.data["error"])

    def test_heartbeat_rejects_non_numeric_attempt_id(self):
        self._login("candidate@test.com")
        res = self.client.post(
            "/api/monitoring/heartbeat/",
            {"attempt_id": "xyz"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_exam_create_rejects_zero_duration(self):
        self._login("admin@test.com")
        start = now()
        res = self.client.post(
            "/api/admin/exam/create/",
            {
                "title": "Bad Exam",
                "description": "",
                "duration": 0,
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(days=1)).isoformat(),
                "questions": [
                    {
                        "text": "Q",
                        "question_type": "mcq",
                        "points": 1,
                        "options": [
                            {"text": "A", "is_correct": True},
                            {"text": "B", "is_correct": False},
                        ],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_live_monitor_query_count_bounded(self):
        self._login("admin@test.com")
        attempt = ExamAttempt.objects.create(
            user=self.candidate, exam=self.exam, status="active", last_active=now()
        )
        from monitoring.models import Violation, Screenshot

        Violation.objects.create(attempt=attempt, violation_type="tab_switch", severity=3)
        Screenshot.objects.create(attempt=attempt, image="https://example.com/s.png")

        from admin_panel.views import live_monitor
        from rest_framework.test import APIRequestFactory, force_authenticate

        factory = APIRequestFactory()
        request = factory.get(f"/api/admin/exam/{self.exam.id}/live/")
        force_authenticate(request, user=self.admin)

        with CaptureQueriesContext(connection) as ctx:
            response = live_monitor(request, self.exam.id)

        self.assertEqual(response.status_code, 200)
        # 1 exam lookup + 1 attempts prefetch (violations + screenshots) + permission overhead
        self.assertLessEqual(len(ctx.captured_queries), 8)

    def test_user_detail_no_duplicate_images_key(self):
        self._login("admin@test.com")
        attempt = ExamAttempt.objects.create(user=self.candidate, exam=self.exam, status="active")
        from monitoring.models import Screenshot

        Screenshot.objects.create(attempt=attempt, image="https://example.com/a.png")
        res = self.client.get(f"/api/admin/user/{self.candidate.email}/")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("images", res.data)
        self.assertIn("screenshots", res.data)

    @patch("cloudinary.uploader.upload", side_effect=TimeoutError("timeout"))
    def test_screenshot_upload_graceful_failure(self, _mock_upload):
        self._login("candidate@test.com")
        start = self.client.post(f"/api/exams/{self.exam.id}/start/", format="json")
        from django.core.files.uploadedfile import SimpleUploadedFile

        image = SimpleUploadedFile("test.jpg", b"fake", content_type="image/jpeg")
        res = self.client.post(
            "/api/monitoring/screenshot/",
            {"attempt_id": start.data["attempt_id"], "image": image},
            format="multipart",
        )
        self.assertEqual(res.status_code, 202)
        self.assertIn("skipped", res.data.get("status", ""))
