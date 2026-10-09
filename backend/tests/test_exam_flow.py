from datetime import timedelta
from unittest import mock

from django.test import override_settings
from django.utils.timezone import now

from attempt_events.models import AttemptEvent
from exams.models import Answer, ExamAttempt

from .helpers import ApiTestCase, PhoneKey


class ExamFlowTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.student = self.add_member("student@example.com")
        self.phone = self.approved_phone(self.student)
        self.client_s = self.client_for(self.student, self.phone)
        self.exam = self.make_exam()

    # --- question gating (C-1) ---------------------------------------------
    def test_detail_has_no_questions_before_start(self):
        res = self.client_s.get(f"/api/exams/{self.exam.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.data["questions"])
        self.assertIn("server_time", res.data)

    def test_detail_returns_shuffled_questions_during_attempt_without_answers(self):
        self.assertEqual(self.start(self.client_s, self.phone, self.exam).status_code, 200)
        first = self.client_s.get(f"/api/exams/{self.exam.id}/").data
        second = self.client_s.get(f"/api/exams/{self.exam.id}/").data
        self.assertEqual(len(first["questions"]), 3)
        self.assertEqual(first["questions"], second["questions"])  # stable per attempt
        for q in first["questions"]:
            for option in q["options"]:
                self.assertEqual(set(option), {"id", "text"})  # no is_correct leak

    def test_detail_hides_questions_after_completion(self):
        self.start(self.client_s, self.phone, self.exam)
        self.client_s.post(f"/api/exams/{self.exam.id}/submit/", {"answers": {}}, format="json")
        self.assertIsNone(self.client_s.get(f"/api/exams/{self.exam.id}/").data["questions"])

    # --- device binding / challenge (H-5) ----------------------------------
    def test_exam_endpoints_require_approved_device(self):
        no_device = self.client_for(self.student)
        res = no_device.get(f"/api/exams/{self.exam.id}/")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data["code"], "device_not_approved")
        other_phone = PhoneKey("unregistered")
        res = self.client_for(self.student, other_phone).post(f"/api/exams/{self.exam.id}/challenge/")
        self.assertEqual(res.data["code"], "device_not_approved")

    def test_start_requires_valid_challenge_and_signature(self):
        res = self.client_s.post(f"/api/exams/{self.exam.id}/start/", {}, format="json")
        self.assertEqual(res.data["code"], "challenge_invalid")

        challenge = self.client_s.post(f"/api/exams/{self.exam.id}/challenge/").data
        forged = PhoneKey("attacker").sign(challenge["sign_payload"])
        res = self.client_s.post(f"/api/exams/{self.exam.id}/start/",
                                 {"nonce": challenge["nonce"], "signature": forged}, format="json")
        self.assertEqual(res.data["code"], "signature_invalid")

        # nonce is single-use even after a failed attempt
        res = self.client_s.post(f"/api/exams/{self.exam.id}/start/",
                                 {"nonce": challenge["nonce"],
                                  "signature": self.phone.sign(challenge["sign_payload"])},
                                 format="json")
        self.assertEqual(res.data["code"], "challenge_invalid")

        res = self.start(self.client_s, self.phone, self.exam)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["resumed"])
        attempt = ExamAttempt.objects.get(pk=res.data["attempt_id"])
        self.assertEqual(attempt.device.device_id, self.phone.device_id)

        res = self.start(self.client_s, self.phone, self.exam)
        self.assertTrue(res.data["resumed"])

    def test_unpublished_exam_cannot_be_started(self):
        self.exam.is_published = False
        self.exam.save()
        res = self.client_s.post(f"/api/exams/{self.exam.id}/challenge/")
        self.assertEqual(res.status_code, 404)

    def test_disabled_member_cannot_start(self):
        self.student.memberships.update(is_exam_enabled=False)
        res = self.start(self.client_s, self.phone, self.exam)
        self.assertEqual(res.data["code"], "access_disabled")

    # --- grading on every exit path (H-2) -----------------------------------
    def _save(self, attempt_id, question, option_id):
        return self.client_s.post("/api/exams/answers/save/", {
            "attempt_id": attempt_id, "question_id": question.id, "answer": option_id,
        }, format="json")

    def test_save_and_submit_grades(self):
        attempt_id = self.start(self.client_s, self.phone, self.exam).data["attempt_id"]
        self.assertEqual(self._save(attempt_id, self.questions[0],
                                    self.correct[self.questions[0].id]).status_code, 200)
        res = self.client_s.post(f"/api/exams/{self.exam.id}/submit/", {
            "answers": {str(self.questions[1].id): self.correct[self.questions[1].id]},
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["points_scored"], 4)
        self.assertEqual(res.data["end_reason"], "submitted")
        # idempotent retry
        again = self.client_s.post(f"/api/exams/{self.exam.id}/submit/", {"answers": {}}, format="json")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.data["points_scored"], 4)

    def test_expiry_auto_submits_saved_answers_instead_of_zero(self):
        attempt_id = self.start(self.client_s, self.phone, self.exam).data["attempt_id"]
        self._save(attempt_id, self.questions[0], self.correct[self.questions[0].id])
        ExamAttempt.objects.filter(pk=attempt_id).update(deadline=now() - timedelta(minutes=5))
        res = self._save(attempt_id, self.questions[1], self.correct[self.questions[1].id])
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data["code"], "attempt_ended")
        attempt = ExamAttempt.objects.get(pk=attempt_id)
        self.assertEqual(attempt.status, "completed")
        self.assertEqual(attempt.end_reason, "deadline_expired")
        self.assertEqual(attempt.points_scored, 2)

    def test_submit_within_grace_accepts_final_answers(self):
        attempt_id = self.start(self.client_s, self.phone, self.exam).data["attempt_id"]
        ExamAttempt.objects.filter(pk=attempt_id).update(deadline=now() - timedelta(seconds=3))
        res = self.client_s.post(f"/api/exams/{self.exam.id}/submit/", {
            "answers": {str(q.id): self.correct[q.id] for q in self.questions},
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["points_scored"], 6)

    def test_submit_after_grace_grades_only_saved(self):
        attempt_id = self.start(self.client_s, self.phone, self.exam).data["attempt_id"]
        self._save(attempt_id, self.questions[0], self.correct[self.questions[0].id])
        ExamAttempt.objects.filter(pk=attempt_id).update(deadline=now() - timedelta(minutes=2))
        res = self.client_s.post(f"/api/exams/{self.exam.id}/submit/", {
            "answers": {str(q.id): self.correct[q.id] for q in self.questions},
        }, format="json")
        # Late submit still returns the result, but late answers are ignored.
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["points_scored"], 2)
        attempt = ExamAttempt.objects.get(pk=attempt_id)
        self.assertEqual(attempt.points_scored, 2)
        self.assertEqual(attempt.end_reason, "deadline_expired")

    def test_answer_length_capped(self):
        from exams.models import Question
        q = Question.objects.create(exam=self.exam, text="short", question_type="short_answer",
                                    points=1, correct_text_answer="x")
        attempt_id = self.start(self.client_s, self.phone, self.exam).data["attempt_id"]
        res = self.client_s.post("/api/exams/answers/save/", {
            "attempt_id": attempt_id, "question_id": q.id, "answer": "a" * 6000,
        }, format="json")
        self.assertEqual(res.data["code"], "invalid_answer")

    def test_other_org_attempt_is_invisible(self):
        attempt_id = self.start(self.client_s, self.phone, self.exam).data["attempt_id"]
        from organisations.models import Organisation, OrganisationMember
        other_org = Organisation.objects.create(name="Other", slug="other", owner=self.owner, status="approved")
        intruder = self.make_user("intruder@example.com")
        OrganisationMember.objects.create(organisation=other_org, user=intruder, role="candidate")
        self.set_org(intruder, other_org)
        intruder_client = self.client_for(intruder, self.approved_phone(intruder))
        res = intruder_client.post("/api/exams/answers/save/", {
            "attempt_id": attempt_id, "question_id": self.questions[0].id, "answer": 1,
        }, format="json")
        self.assertEqual(res.status_code, 404)

    # --- Play Integrity gate ----------------------------------------------
    @override_settings(INTEGRITY_REQUIRED=True, PLAY_INTEGRITY_PACKAGE="com.parallaxlane.app")
    def test_integrity_gate(self):
        from core import integrity

        def payload_for(nonce, device="MEETS_DEVICE_INTEGRITY", app="PLAY_RECOGNIZED"):
            import time
            return {
                "requestDetails": {"requestPackageName": "com.parallaxlane.app",
                                   "requestHash": integrity.request_hash_for(nonce),
                                   "timestampMillis": str(int(time.time() * 1000))},
                "appIntegrity": {"appRecognitionVerdict": app},
                "deviceIntegrity": {"deviceRecognitionVerdict": [device]},
            }

        def run(make_payload):
            challenge = self.client_s.post(f"/api/exams/{self.exam.id}/challenge/").data
            with mock.patch.object(integrity, "decode_token",
                                   side_effect=lambda token: make_payload(challenge["nonce"])):
                return self.client_s.post(f"/api/exams/{self.exam.id}/start/", {
                    "nonce": challenge["nonce"],
                    "signature": self.phone.sign(challenge["sign_payload"]),
                    "integrity_token": "tok",
                }, format="json")

        res = run(lambda n: payload_for(n, device="MEETS_BASIC_INTEGRITY"))
        self.assertEqual(res.data["code"], "integrity_failed")
        res = run(lambda n: payload_for("some-other-nonce"))
        self.assertEqual(res.data["reason"], "request_hash_mismatch")
        res = run(lambda n: payload_for(n, app="UNRECOGNIZED_VERSION"))
        self.assertEqual(res.data["reason"], "app_not_recognized")

        def boom(n):
            raise integrity.IntegrityUnavailable("down")
        res = run(boom)
        self.assertEqual(res.status_code, 503)

        res = run(payload_for)
        self.assertEqual(res.status_code, 200)


class LegacyWebModeTests(ApiTestCase):
    """DEVICE_REQUIRED_FOR_EXAMS=False keeps the web client usable (no challenge)."""

    @override_settings(DEVICE_REQUIRED_FOR_EXAMS=False)
    def test_start_without_device(self):
        student = self.add_member("web@example.com")
        exam = self.make_exam()
        client = self.client_for(student)
        res = client.post(f"/api/exams/{exam.id}/start/", {}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(client.get(f"/api/exams/{exam.id}/").data["questions"])
