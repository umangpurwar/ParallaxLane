from datetime import timedelta
from unittest import mock

from django.utils.timezone import now

from attempt_events.models import AttemptEvent
from exams.models import ExamAttempt
from monitoring.models import Violation

from .helpers import ApiTestCase


class MonitoringTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.student = self.add_member("student@example.com")
        self.phone = self.approved_phone(self.student)
        self.client_s = self.client_for(self.student, self.phone)
        self.exam = self.make_exam(violation_limit=2)
        self.attempt_id = self.start(self.client_s, self.phone, self.exam).data["attempt_id"]

    def log(self, vtype, metadata=None):
        return self.client_s.post("/api/monitoring/log/", {
            "attempt_id": self.attempt_id, "type": vtype, "metadata": metadata or {},
        }, format="json")

    def test_counted_violations_terminate_with_grading(self):
        self.client_s.post("/api/exams/answers/save/", {
            "attempt_id": self.attempt_id, "question_id": self.questions[0].id,
            "answer": self.correct[self.questions[0].id],
        }, format="json")
        self.assertEqual(self.log("app_backgrounded").data["state"], "active")
        res = self.log("lock_task_exited")
        self.assertEqual(res.data["state"], "terminated")
        self.assertEqual(res.data["code"], "attempt_terminated")
        attempt = ExamAttempt.objects.get(pk=self.attempt_id)
        self.assertEqual(attempt.end_reason, "violation_threshold")
        self.assertEqual(attempt.points_scored, 2)  # graded, not zero
        self.assertEqual(self.log("app_backgrounded").data["code"], "attempt_terminated")

    def test_soft_violations_never_terminate(self):
        for _ in range(5):
            res = self.log("accessibility_service")
        self.assertEqual(res.data["state"], "active")
        self.assertEqual(res.data["violations"], 0)
        self.assertEqual(res.data["risk"], 10)

    def test_server_only_and_unknown_types_rejected(self):
        self.assertEqual(self.log("heartbeat_gap").data["code"], "invalid_violation_type")
        self.assertEqual(self.log("integrity_failed").data["code"], "invalid_violation_type")
        self.assertEqual(self.log("made_up").status_code, 400)

    def test_metadata_whitelisted_and_truncated(self):
        self.log("app_backgrounded", {"duration_ms": 900, "camera": True, "detail": "x" * 500,
                                      "nested": {"a": 1}})
        violation = Violation.objects.get(attempt_id=self.attempt_id)
        self.assertEqual(set(violation.metadata), {"duration_ms", "detail"})
        self.assertEqual(len(violation.metadata["detail"]), 120)

    def test_heartbeat_gap_is_detected_server_side(self):
        res = self.client_s.post("/api/monitoring/heartbeat/", {
            "attempt_id": self.attempt_id, "state": {"foreground": True, "lock_task": True},
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("integrity_nonce", res.data)
        self.assertFalse(Violation.objects.filter(attempt_id=self.attempt_id).exists())

        ExamAttempt.objects.filter(pk=self.attempt_id).update(
            last_active=now() - timedelta(seconds=90))
        res = self.client_s.post("/api/monitoring/heartbeat/", {"attempt_id": self.attempt_id},
                                 format="json")
        self.assertEqual(res.data["state"], "active")
        gap = Violation.objects.get(attempt_id=self.attempt_id)
        self.assertEqual(gap.violation_type, "heartbeat_gap")
        self.assertEqual(ExamAttempt.objects.get(pk=self.attempt_id).total_violations, 0)

    def test_heartbeat_integrity_failure_is_violation(self):
        from core import integrity
        with mock.patch.object(integrity, "decode_token", return_value={"requestDetails": {}}):
            self.client_s.post("/api/monitoring/heartbeat/", {
                "attempt_id": self.attempt_id, "integrity_token": "tok"}, format="json")
        self.assertTrue(Violation.objects.filter(attempt_id=self.attempt_id,
                                                 violation_type="integrity_failed").exists())

    def test_events_batch(self):
        res = self.client_s.post("/api/monitoring/events/", {
            "attempt_id": self.attempt_id,
            "events": [
                {"type": "question_viewed", "question_id": self.questions[0].id, "client_ts": 1},
                {"type": "network_offline"},
                {"type": "exam_submitted"},  # not client-reportable: dropped
            ],
        }, format="json")
        self.assertEqual(res.data["accepted"], 2)
        self.assertFalse(AttemptEvent.objects.filter(attempt_id=self.attempt_id,
                                                     event_type="exam_submitted").exists())

    def test_heartbeat_rate_limit_is_per_user_and_returns_429(self):
        other = self.add_member("other@example.com")
        other_phone = self.approved_phone(other)
        other_client = self.client_for(other, other_phone)
        other_attempt = self.start(other_client, other_phone, self.exam).data["attempt_id"]

        statuses = [
            self.client_s.post("/api/monitoring/heartbeat/", {"attempt_id": self.attempt_id},
                               format="json").status_code
            for _ in range(31)
        ]
        self.assertEqual(statuses[:30], [200] * 30)
        self.assertEqual(statuses[30], 429)
        limited = self.client_s.post("/api/monitoring/heartbeat/",
                                     {"attempt_id": self.attempt_id}, format="json")
        self.assertEqual(limited.data["code"], "rate_limited")
        # A different candidate is unaffected (was a single global bucket before).
        res = other_client.post("/api/monitoring/heartbeat/", {"attempt_id": other_attempt},
                                format="json")
        self.assertEqual(res.status_code, 200)
