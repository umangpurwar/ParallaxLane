from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.urls import reverse
from exams.models import Exam, Question, QuestionOption, ExamAttempt
from monitoring.models import Violation, Screenshot
from organisations.models import Organisation, OrganisationMember, OrganisationInvite
from accounts.models import EmailOTP
from django.utils.timezone import now
from datetime import timedelta
import concurrent.futures
from django.db import connection

User = get_user_model()

class AuditEvidenceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="owner@test.com", email="owner@test.com", password="password")
        self.org = Organisation.objects.create(name="Test Org", slug="test-org", owner=self.user, plan="free", max_candidates=1, max_exams=1)
        OrganisationMember.objects.create(organisation=self.org, user=self.user, role="owner")
        self.user.current_organisation = self.org
        self.user.save()
        self.client.force_authenticate(user=self.user)

        self.exam = Exam.objects.create(
            title="Test Exam", start_time=now() - timedelta(days=1), end_time=now() + timedelta(days=1),
            duration=60, created_by=self.user, organisation=self.org, is_active=True, is_published=True
        )
        self.q1 = Question.objects.create(exam=self.exam, text="Q1", points=10)
        self.q1_opt = QuestionOption.objects.create(question=self.q1, text="Opt 1", is_correct=True)
        self.q2 = Question.objects.create(exam=self.exam, text="Q2", points=10)
        self.q2_opt = QuestionOption.objects.create(question=self.q2, text="Opt 2", is_correct=True)

    def test_bl_001_exam_scoring_flaw(self):
        attempt = ExamAttempt.objects.create(user=self.user, exam=self.exam)
        response = self.client.post(f'/api/exams/{self.exam.id}/submit/', {
            "answers": {
                str(self.q1.id): self.q1_opt.id
            }
        }, format='json')
        self.assertEqual(response.status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual(attempt.points_scored, 10)
        self.assertEqual(attempt.total_points, 20, "Total points should be 20, but the bug makes it 10")

    def test_perf_001_live_monitor_queries(self):
        cand1 = User.objects.create_user(username="c1@test.com", email="c1@test.com")
        OrganisationMember.objects.create(organisation=self.org, user=cand1, role="candidate")
        attempt1 = ExamAttempt.objects.create(user=cand1, exam=self.exam)
        for _ in range(5):
            Violation.objects.create(attempt=attempt1, violation_type="tab_switch")
            Screenshot.objects.create(attempt=attempt1, image="http://test.com/img.jpg")

        with self.assertNumQueries(5):
            response = self.client.get(f'/api/admin/exam/{self.exam.id}/live/')
            self.assertEqual(response.status_code, 200)

    def test_bl_002_invite_plan_bypass(self):
        inv1 = OrganisationInvite.objects.create(organisation=self.org, email="inv1@test.com", role="candidate", token="token1")
        inv2 = OrganisationInvite.objects.create(organisation=self.org, email="inv2@test.com", role="candidate", token="token2")
        
        user1 = User.objects.create_user(username="inv1@test.com", email="inv1@test.com")
        self.client.force_authenticate(user=user1)
        r1 = self.client.post('/api/organisations/join/', {"code": "token1"})
        self.assertEqual(r1.status_code, 200)
        
        user2 = User.objects.create_user(username="inv2@test.com", email="inv2@test.com")
        self.client.force_authenticate(user=user2)
        r2 = self.client.post('/api/organisations/join/', {"code": "token2"})
        self.assertEqual(r2.status_code, 400, "Second join should fail due to plan limit (max_candidates=1)")

    def test_auth_001_password_validation(self):
        otp = EmailOTP.objects.create(email="newuser@test.com", otp="123456")
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/accounts/verify-otp-register/', {
            "email": "newuser@test.com",
            "otp": "123456",
            "name": "New User",
            "password": "1" # Weak password
        }, format='json')
        self.assertEqual(response.status_code, 400, "Weak password should be rejected")


class AuditEvidenceTransactionTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner@test.com", email="owner@test.com", password="password")
        self.org = Organisation.objects.create(name="Test Org", slug="test-org", owner=self.user, plan="free", max_exams=1)
        OrganisationMember.objects.create(organisation=self.org, user=self.user, role="owner")
        self.user.current_organisation = self.org
        self.user.save()

    @override_settings(RATELIMIT_ENABLE=False)
    def test_race_001_concurrent_exam_create(self):
        def create_exam_request():
            client = APIClient()
            client.force_authenticate(user=self.user)
            res = client.post('/api/admin/exam/create/', {
                "title": "Race Exam",
                "duration": 60,
                "start_time": now() - timedelta(days=1),
                "end_time": now() + timedelta(days=1),
                "questions": [{"text": "Q1", "points": 1, "question_type": "mcq", "options": [{"text": "Opt1", "is_correct": True}]}]
            }, format='json')
            connection.close()
            return res.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_exam_request) for _ in range(5)]
            results = [f.result() for f in futures]
        
        self.assertEqual(Exam.objects.count(), 1, "Only 1 exam should be created due to max_exams=1")
