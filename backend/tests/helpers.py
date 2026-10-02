import base64
import hashlib
from datetime import timedelta

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.cache import cache
from django.test import TestCase
from django.utils.timezone import now
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User, UserDevice
from exams.models import Exam, Question, QuestionOption
from organisations.models import Organisation, OrganisationMember


class PhoneKey:
    """Stand-in for an Android Keystore EC P-256 key."""

    def __init__(self, seed):
        self.private = ec.generate_private_key(ec.SECP256R1())
        self.device_id = hashlib.sha256(seed.encode()).hexdigest()

    @property
    def public_b64(self):
        der = self.private.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(der).decode()

    def sign(self, message):
        return base64.b64encode(
            self.private.sign(message.encode(), ec.ECDSA(hashes.SHA256()))
        ).decode()


class ApiTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = self.make_user("owner@example.com")
        self.org = Organisation.objects.create(name="Test Org", slug="test-org", owner=self.owner,
                                               plan="enterprise", max_exams=50)
        OrganisationMember.objects.create(organisation=self.org, user=self.owner, role="owner")
        self.set_org(self.owner, self.org)

    # --- users -----------------------------------------------------------
    def make_user(self, email, active=True):
        user = User.objects.create_user(username=email, email=email, password="Str0ng-pass-123",
                                        is_active=active)
        user.email_verified = active
        user.save(update_fields=["email_verified"])
        return user

    def set_org(self, user, org):
        user.current_organisation = org
        user.save(update_fields=["current_organisation"])

    def add_member(self, email, role="candidate", org=None):
        org = org or self.org
        user = self.make_user(email)
        OrganisationMember.objects.create(organisation=org, user=user, role=role)
        self.set_org(user, org)
        return user

    def client_for(self, user, phone=None, headers=None):
        client = APIClient()
        token = str(RefreshToken.for_user(user).access_token)
        extra = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        if phone is not None:
            extra["HTTP_X_DEVICE_ID"] = phone.device_id
        extra.update(headers or {})
        client.credentials(**extra)
        return client

    def approved_phone(self, user, seed=None):
        phone = PhoneKey(seed or f"phone-{user.email}")
        UserDevice.objects.create(user=user, device_id=phone.device_id,
                                  public_key=phone.public_b64, status="approved")
        return phone

    # --- exams -----------------------------------------------------------
    def make_exam(self, duration=30, starts_in=-5, ends_in=120, violation_limit=3):
        exam = Exam.objects.create(
            title="Physics", start_time=now() + timedelta(minutes=starts_in),
            end_time=now() + timedelta(minutes=ends_in), duration=duration,
            created_by=self.owner, organisation=self.org, is_active=True,
            is_published=True, violation_limit=violation_limit,
        )
        self.questions = []
        self.correct = {}
        for i in range(3):
            q = Question.objects.create(exam=exam, text=f"Q{i}", question_type="mcq",
                                        points=2, order=i)
            right = QuestionOption.objects.create(question=q, text="right", is_correct=True)
            QuestionOption.objects.create(question=q, text="wrong", is_correct=False)
            self.questions.append(q)
            self.correct[q.id] = right.id
        return exam

    def start(self, client, phone, exam, integrity_token=None):
        challenge = client.post(f"/api/exams/{exam.id}/challenge/")
        assert challenge.status_code == 200, challenge.content
        body = {"nonce": challenge.data["nonce"],
                "signature": phone.sign(challenge.data["sign_payload"])}
        if integrity_token:
            body["integrity_token"] = integrity_token
        return client.post(f"/api/exams/{exam.id}/start/", body, format="json")
