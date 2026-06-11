from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils.timezone import now
from rest_framework.test import APIClient

from exams.models import Exam, ExamAttempt, Question, QuestionOption
from monitoring.models import Violation
from organisations.models import Organisation, OrganisationInvite, OrganisationMember

User = get_user_model()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
    RATELIMIT_ENABLE=False,
)
class SmokeTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="TestPass1!",
            name="Admin User",
        )
        self.candidate = User.objects.create_user(
            username="candidate@test.com",
            email="candidate@test.com",
            password="TestPass1!",
            name="Candidate User",
        )

    def _login(self, email, password):
        res = self.client.post("/api/login/", {"email": email, "password": password}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def test_register_and_login(self):
        res = self.client.post(
            "/api/accounts/register/",
            {"email": "new@test.com", "password": "TestPass1!", "name": "New User"},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)

        login = self.client.post(
            "/api/login/",
            {"email": "new@test.com", "password": "TestPass1!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("refresh", login.data)

    def test_org_create_switch_and_join(self):
        self._login("admin@test.com", "TestPass1!")

        create_res = self.client.post(
            "/api/organisations/create/",
            {"name": "Test Org"},
            format="json",
        )
        self.assertEqual(create_res.status_code, 200, create_res.data)
        slug = create_res.data["slug"]

        list_res = self.client.get("/api/organisations/my/")
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(list_res.data["count"], 1)
        self.assertEqual(list_res.data["organisations"][0]["slug"], slug)

        switch_res = self.client.post(f"/api/organisations/{slug}/switch/", format="json")
        self.assertEqual(switch_res.status_code, 200)
        self.assertEqual(switch_res.data["slug"], slug)

    def test_exam_create_start_submit(self):
        self._login("admin@test.com", "TestPass1!")
        org = Organisation.objects.create(name="Exam Org", slug="exam-org", owner=self.admin)
        OrganisationMember.objects.create(organisation=org, user=self.admin, role="owner")
        OrganisationMember.objects.create(organisation=org, user=self.candidate, role="candidate")
        self.admin.current_organisation = org
        self.admin.save()
        self.candidate.current_organisation = org
        self.candidate.save()

        start = now()
        end = start + timedelta(days=1)
        exam_payload = {
            "title": "Smoke Exam",
            "description": "Test",
            "duration": 30,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "questions": [
                {
                    "text": "What is 2+2?",
                    "question_type": "mcq",
                    "points": 1,
                    "options": [
                        {"text": "3", "is_correct": False},
                        {"text": "4", "is_correct": True},
                    ],
                }
            ],
        }

        create_res = self.client.post("/api/admin/exam/create/", exam_payload, format="json")
        self.assertEqual(create_res.status_code, 200, create_res.data)
        exam_id = create_res.data["exam_id"]

        exam = Exam.objects.get(id=exam_id)
        exam.is_active = True
        exam.save()

        self.client.credentials()
        candidate_tokens = self._login("candidate@test.com", "TestPass1!")

        start_res = self.client.post(f"/api/exams/{exam_id}/start/", format="json")
        self.assertEqual(start_res.status_code, 200, start_res.data)
        attempt_id = start_res.data["attempt_id"]

        question = Question.objects.get(exam_id=exam_id)
        correct_option = QuestionOption.objects.get(question=question, is_correct=True)

        submit_res = self.client.post(
            f"/api/exams/{exam_id}/submit/",
            {"answers": {str(question.id): correct_option.id}},
            format="json",
        )
        self.assertEqual(submit_res.status_code, 200, submit_res.data)
        self.assertEqual(submit_res.data["points_scored"], 1)

        logout_res = self.client.post(
            "/api/accounts/logout/",
            {"refresh": candidate_tokens["refresh"]},
            format="json",
        )
        self.assertEqual(logout_res.status_code, 200)

    def test_login_auto_accepts_pending_invite(self):
        org = Organisation.objects.create(name="Join Org", slug="join-org", owner=self.admin)
        OrganisationMember.objects.create(organisation=org, user=self.admin, role="owner")
        OrganisationInvite.objects.create(
            organisation=org, email="candidate@test.com", role="candidate", token="test-invite-token"
        )

        login_data = self._login("candidate@test.com", "TestPass1!")
        self.assertEqual(login_data["org_slug"], "join-org")
        self.assertEqual(login_data["org_role"], "candidate")

    def test_register_auto_accepts_pending_invite(self):
        org = Organisation.objects.create(name="Invite Org", slug="invite-org", owner=self.admin)
        OrganisationMember.objects.create(organisation=org, user=self.admin, role="owner")
        OrganisationInvite.objects.create(
            organisation=org,
            email="newinvite@test.com",
            role="candidate",
            token="pending-invite-token",
        )

        EmailOTP = __import__("accounts.models", fromlist=["EmailOTP"]).EmailOTP
        EmailOTP.objects.create(email="newinvite@test.com", otp="123456")

        res = self.client.post(
            "/api/accounts/verify-otp-register/",
            {
                "email": "newinvite@test.com",
                "otp": "123456",
                "name": "Invited User",
                "password": "TestPass1!",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn("access", res.data)
        self.assertEqual(res.data["org_slug"], "invite-org")
        self.assertEqual(res.data["org_role"], "candidate")

    def test_health_check(self):
        res = self.client.get("/api/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_exam_export_report(self):
        self._login("admin@test.com", "TestPass1!")
        org = Organisation.objects.create(name="Report Org", slug="report-org", owner=self.admin)
        OrganisationMember.objects.create(organisation=org, user=self.admin, role="owner")
        self.admin.current_organisation = org
        self.admin.save()

        start = now()
        end = start + timedelta(days=1)
        exam = Exam.objects.create(
            title="Django Basics",
            description="Export test",
            duration=30,
            start_time=start,
            end_time=end,
            created_by=self.admin,
            organisation=org,
            is_active=True,
        )

        attempt = ExamAttempt.objects.create(
            user=self.candidate,
            exam=exam,
            points_scored=42,
            total_points=50,
            status="completed",
            end_time=now(),
            risk_score=3,
            total_violations=2,
        )
        Violation.objects.create(attempt=attempt, violation_type="tab_switch", severity=3)
        Violation.objects.create(attempt=attempt, violation_type="tab_switch", severity=3)

        res = self.client.get(f"/api/admin/exam/{exam.id}/export/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("ParallaxLane_Assessment_Report.xlsx", res["Content-Disposition"])
        self.assertGreater(len(res.content), 1000)
