from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils.timezone import now
from rest_framework.test import APIClient

from accounts.models import EmailOTP
from organisations.models import Organisation, OrganisationInvite, OrganisationMember

User = get_user_model()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
    RATELIMIT_ENABLE=False,
    GOOGLE_OAUTH_CLIENT_ID="test-client-id.apps.googleusercontent.com",
    OTP_MAX_VERIFY_ATTEMPTS=3,
    OTP_LOCKOUT_SECONDS=60,
    OTP_VERIFY_WINDOW_SECONDS=300,
)
class SecurityRemediationTestCase(TestCase):
    def setUp(self):
        cache.clear()
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
        self.other = User.objects.create_user(
            username="other@test.com",
            email="other@test.com",
            password="TestPass1!",
            name="Other User",
        )
        self.org = Organisation.objects.create(name="Sec Org", slug="sec-org", owner=self.admin)
        OrganisationMember.objects.create(organisation=self.org, user=self.admin, role="owner")
        self.admin.current_organisation = self.org
        self.admin.save()

    def _login(self, email):
        res = self.client.post(
            "/api/login/",
            {"email": email, "password": "TestPass1!"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def test_send_otp_never_returns_otp_value(self):
        res = self.client.post(
            "/api/accounts/send-otp/",
            {"email": "candidate@test.com", "mode": "login"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("dev_otp", res.data)
        self.assertNotIn("otp", res.data)

    def test_otp_lockout_after_failed_attempts(self):
        EmailOTP.objects.create(email="candidate@test.com", otp="111111")
        for _ in range(3):
            res = self.client.post(
                "/api/accounts/verify-otp/",
                {"email": "candidate@test.com", "otp": "000000"},
                format="json",
            )
            self.assertEqual(res.status_code, 400)

        locked = self.client.post(
            "/api/accounts/verify-otp/",
            {"email": "candidate@test.com", "otp": "111111"},
            format="json",
        )
        self.assertEqual(locked.status_code, 429)

    def test_invite_rejects_owner_role(self):
        self._login("admin@test.com")
        res = self.client.post(
            f"/api/organisations/{self.org.slug}/invite/",
            {"email": "newowner@test.com", "role": "owner"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_invite_rejects_invalid_role(self):
        self._login("admin@test.com")
        res = self.client.post(
            f"/api/organisations/{self.org.slug}/invite/",
            {"email": "hacker@test.com", "role": "superadmin"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_invite_accepts_valid_staff_role(self):
        self._login("admin@test.com")
        res = self.client.post(
            f"/api/organisations/{self.org.slug}/invite/",
            {"email": "invig@test.com", "role": "invigilator"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

    def test_accept_invite_requires_matching_email(self):
        invite = OrganisationInvite.objects.create(
            organisation=self.org,
            email="candidate@test.com",
            role="candidate",
            token="email-match-token",
            expires_at=now() + timedelta(days=1),
        )
        self._login("other@test.com")
        res = self.client.post(
            "/api/organisations/join/",
            {"code": invite.token},
            format="json",
        )
        self.assertEqual(res.status_code, 403)
        invite.refresh_from_db()
        self.assertFalse(invite.accepted)

    @patch("accounts.google_auth.id_token.verify_oauth2_token")
    def test_google_auth_rejects_wrong_audience(self, mock_verify):
        mock_verify.side_effect = ValueError("Token has wrong audience")
        res = self.client.post(
            "/api/accounts/google/",
            {"token": "fake-token"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    @patch("accounts.google_auth.id_token.verify_oauth2_token")
    def test_google_auth_accepts_valid_token(self, mock_verify):
        mock_verify.return_value = {
            "email": "google@test.com",
            "email_verified": True,
            "iss": "accounts.google.com",
            "name": "Google User",
            "given_name": "Google",
        }
        res = self.client.post(
            "/api/accounts/google/",
            {"token": "valid-token"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_switch_org_rejects_inactive_membership(self):
        inactive_org = Organisation.objects.create(
            name="Inactive Org", slug="inactive-org", owner=self.admin
        )
        OrganisationMember.objects.create(
            organisation=inactive_org,
            user=self.candidate,
            role="candidate",
            is_active=False,
        )
        self._login("candidate@test.com")
        res = self.client.post("/api/organisations/inactive-org/switch/", format="json")
        self.assertEqual(res.status_code, 403)

    def test_update_exam_enforces_plan_question_limit(self):
        from exams.models import Exam, Question

        self._login("admin@test.com")
        start = now()
        exam = Exam.objects.create(
            title="Plan Limit Exam",
            description="",
            duration=30,
            start_time=start,
            end_time=start + timedelta(days=1),
            created_by=self.admin,
            organisation=self.org,
        )
        Question.objects.create(exam=exam, text="Q1", question_type="mcq", points=1)

        questions = [
            {
                "text": f"Question {i}",
                "question_type": "mcq",
                "points": 1,
                "options": [
                    {"text": "A", "is_correct": True},
                    {"text": "B", "is_correct": False},
                ],
            }
            for i in range(11)
        ]

        res = self.client.patch(
            f"/api/admin/exam/{exam.id}/update/",
            {
                "title": exam.title,
                "description": exam.description,
                "duration": exam.duration,
                "start_time": exam.start_time.isoformat(),
                "end_time": exam.end_time.isoformat(),
                "questions": questions,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", str(res.data).lower())

    def test_candidate_cannot_access_admin_export(self):
        OrganisationMember.objects.create(
            organisation=self.org, user=self.candidate, role="candidate"
        )
        self.candidate.current_organisation = self.org
        self.candidate.save()
        self._login("candidate@test.com")

        from exams.models import Exam

        exam = Exam.objects.create(
            title="Sec Exam",
            description="",
            duration=30,
            start_time=now(),
            end_time=now() + timedelta(days=1),
            created_by=self.admin,
            organisation=self.org,
        )

        res = self.client.get(f"/api/admin/exam/{exam.id}/export/")
        self.assertIn(res.status_code, [403, 401])
