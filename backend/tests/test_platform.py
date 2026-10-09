"""Organisation approval, super admin protection, isolation and invitations.

Each test names the attack or mistake it covers and asserts the safe outcome:
rejected request, no partial records, no role change.
"""

import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.utils.timezone import now
from datetime import timedelta

from accounts.models import EmailOTP, User
from admin_panel.models import AuditLog
from exams.models import ExamAttempt
from organisations.models import Organisation, OrganisationInvite, OrganisationMember

from .helpers import ApiTestCase

APPLY = {"name": "Riverside College", "description": "Weekly class tests for 300 students"}


class PlatformTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.superadmin = User.objects.create_superuser(
            username="root@example.com", email="root@example.com", password="Sup3r-secret-pass")
        self.super_client = self.client_for(self.superadmin)

    def apply(self, user, data=None):
        return self.client_for(user).post("/api/organisations/create/", data or APPLY, format="json")

    def act(self, org_id, action, client=None, note="reason"):
        client = client or self.super_client
        return client.post(f"/api/master-admin/organisations/{org_id}/{action}/", {"note": note}, format="json")


class ApplicationLifecycleTests(PlatformTestCase):
    def test_application_is_pending_and_cannot_operate(self):
        applicant = self.make_user("head@riverside.edu")
        res = self.apply(applicant)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "pending")
        org = Organisation.objects.get(pk=res.data["id"])
        self.assertFalse(org.is_active)
        self.set_org(applicant, org)
        client = self.client_for(applicant)
        # pending: invite, create exam, list exams, overview, join code are all refused
        self.assertEqual(client.post(f"/api/organisations/{org.slug}/invite/", {"email": "s@x.com"}, format="json").status_code, 404)
        self.assertEqual(client.post("/api/admin/exam/create/", {}, format="json").status_code, 403)
        self.assertEqual(client.get("/api/exams/").status_code, 403)
        self.assertEqual(client.get(f"/api/organisations/{org.slug}/overview/").status_code, 403)
        self.assertEqual(client.get(f"/api/organisations/{org.slug}/join-code/").status_code, 404)
        self.assertEqual(client.get("/api/exams/").data["code"], "organisation_unavailable")

    def test_approval_unlocks_and_is_audited(self):
        applicant = self.make_user("head@riverside.edu")
        org_id = self.apply(applicant).data["id"]
        res = self.act(org_id, "approve")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "approved")
        org = Organisation.objects.get(pk=org_id)
        self.set_org(applicant, org)
        res = self.client_for(applicant).post(f"/api/organisations/{org.slug}/invite/", {"email": "s@x.com"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="organisation_approve", organisation=org, actor=self.superadmin).exists())

    def test_only_super_admin_can_review(self):
        applicant = self.make_user("head@riverside.edu")
        org_id = self.apply(applicant).data["id"]
        org_admin = self.owner  # owner of the approved Test Org
        for client in (self.client_for(applicant), self.client_for(org_admin), self.client_for(self.add_member("m@x.com"))):
            self.assertEqual(self.act(org_id, "approve", client=client).status_code, 403)
        self.assertEqual(self.client.post(f"/api/master-admin/organisations/{org_id}/approve/").status_code, 401)
        self.assertEqual(Organisation.objects.get(pk=org_id).status, "pending")

    def test_invalid_transitions_and_double_approval(self):
        applicant = self.make_user("head@riverside.edu")
        org_id = self.apply(applicant).data["id"]
        self.assertEqual(self.act(org_id, "suspend").status_code, 409)
        self.assertEqual(self.act(org_id, "reject", note="").data["code"], "note_required")
        self.assertEqual(self.act(org_id, "approve").status_code, 200)
        self.assertEqual(self.act(org_id, "approve").data["code"], "invalid_transition")
        self.assertEqual(self.act(org_id, "nonsense").status_code, 404)
        self.assertEqual(AuditLog.objects.filter(action="organisation_approve").count(), 1)

    def test_rejected_cannot_operate_or_reapply_around_rejection(self):
        applicant = self.make_user("head@riverside.edu")
        org_id = self.apply(applicant).data["id"]
        self.act(org_id, "reject", note="Could not verify the college")
        res = self.apply(applicant, {"name": "Riverside College Two", "description": "again"})
        self.assertEqual(res.data["code"], "application_rejected")
        self.assertEqual(Organisation.objects.filter(owner=applicant).count(), 1)
        mine = self.client_for(applicant).get("/api/organisations/applications/mine/").data
        self.assertEqual(mine[0]["review_note"], "Could not verify the college")
        # The supported path: fix and resubmit the same record, which goes back to review.
        res = self.client_for(applicant).post(f"/api/organisations/applications/{org_id}/resubmit/",
                                              {"description": "Now with registration number 123"}, format="json")
        self.assertEqual(res.data["status"], "pending")
        self.assertEqual(self.client_for(applicant).post(
            f"/api/organisations/applications/{org_id}/resubmit/", {}, format="json").status_code, 409)

    def test_duplicates(self):
        applicant = self.make_user("head@riverside.edu")
        self.apply(applicant)
        self.assertEqual(self.apply(applicant).data["code"], "application_pending")
        other = self.make_user("other@riverside.edu")
        res = self.apply(other, {"name": "  RIVERSIDE college ", "description": "x"})
        self.assertEqual(res.data["code"], "name_taken")
        self.assertEqual(self.apply(self.owner, {"name": "Second Org", "description": "x"}).data["code"], "organisation_exists")
        # The database itself refuses a second pending application even if code checks were skipped.
        with self.assertRaises(IntegrityError), transaction.atomic():
            Organisation.objects.create(name="Sneaky", slug="sneaky", owner=applicant, status="pending")

    def test_unverified_email_and_closed_applications(self):
        unverified = self.make_user("new@x.com")
        unverified.email_verified = False
        unverified.save()
        self.assertEqual(self.apply(unverified).data["code"], "email_not_verified")
        self.super_client.patch("/api/master-admin/settings/organisation-creation/",
                                {"organisation_creation_enabled": False}, format="json")
        self.assertEqual(self.apply(self.make_user("late@x.com")).data["code"], "applications_closed")

    def test_protected_fields_in_application_are_ignored(self):
        applicant = self.make_user("head@riverside.edu")
        res = self.apply(applicant, {**APPLY, "status": "approved", "is_active": True, "owner": self.superadmin.id,
                                     "plan": "enterprise", "max_exams": 999, "role": "SUPER_ADMIN"})
        org = Organisation.objects.get(pk=res.data["id"])
        self.assertEqual((org.status, org.is_active, org.owner_id, org.plan, org.max_exams),
                         ("pending", False, applicant.id, "free", 3))
        applicant.refresh_from_db()
        self.assertFalse(applicant.is_superuser or applicant.is_staff)

    def test_suspension_cuts_access_and_ends_running_exams(self):
        student = self.add_member("student@example.com")
        phone = self.approved_phone(student)
        client = self.client_for(student, phone)
        exam = self.make_exam()
        attempt_id = self.start(client, phone, exam).data["attempt_id"]
        client.post("/api/exams/answers/save/", {"attempt_id": attempt_id, "question_id": self.questions[0].id,
                                                  "answer": self.correct[self.questions[0].id]}, format="json")
        self.assertEqual(self.act(self.org.id, "suspend", note="Unpaid").status_code, 200)
        attempt = ExamAttempt.objects.get(pk=attempt_id)
        self.assertEqual((attempt.status, attempt.end_reason, attempt.points_scored),
                         ("terminated", "organisation_suspended", 2))
        # Tokens issued before the suspension stop working for org resources.
        self.assertEqual(client.get("/api/exams/").status_code, 403)
        self.assertEqual(self.client_for(self.owner).get(f"/api/organisations/{self.org.slug}/overview/").status_code, 403)
        self.assertEqual(self.act(self.org.id, "reactivate").status_code, 200)
        self.assertEqual(client.get("/api/exams/").status_code, 200)


class SuperAdminProtectionTests(PlatformTestCase):
    def test_super_admin_cannot_register_or_join_an_organisation(self):
        res = self.apply(self.superadmin)
        self.assertEqual(res.data["code"], "registration_not_allowed")
        self.assertFalse(Organisation.objects.filter(owner=self.superadmin).exists())
        self.org.join_code_enabled = True
        self.org.save()
        res = self.super_client.post("/api/organisations/join-by-code/", {"code": self.org.join_code}, format="json")
        self.assertEqual(res.status_code, 400)
        invite = OrganisationInvite.objects.create(organisation=self.org, email="root@example.com", token="tok-root",
                                                   expires_at=now() + timedelta(days=1))
        self.assertEqual(self.super_client.post("/api/organisations/join/", {"code": invite.token}, format="json").status_code, 400)
        self.assertFalse(OrganisationMember.objects.filter(user=self.superadmin).exists())
        self.superadmin.refresh_from_db()
        self.assertTrue(self.superadmin.is_superuser)

    def test_registering_super_admin_email_does_not_create_or_change_account(self):
        for email in ("root@example.com", "  ROOT@Example.com "):
            record = EmailOTP(email=email.strip().lower())
            record.set_otp("111111")
            record.save()
            res = self.client.post("/api/accounts/verify-otp-register/", {
                "email": email, "otp": "111111", "name": "Mallory", "password": "An0ther-strong-pass"}, format="json")
            self.assertEqual(res.status_code, 400)
        self.assertEqual(User.objects.filter(email__iexact="root@example.com").count(), 1)
        self.assertTrue(User.objects.get(email="root@example.com").check_password("Sup3r-secret-pass"))

    def test_role_fields_in_registration_are_ignored(self):
        record = EmailOTP(email="eve@example.com")
        record.set_otp("222222")
        record.save()
        res = self.client.post("/api/accounts/verify-otp-register/", {
            "email": "eve@example.com", "otp": "222222", "name": "Eve", "password": "An0ther-strong-pass",
            "role": "SUPER_ADMIN", "is_superuser": True, "is_staff": True}, format="json")
        self.assertEqual(res.status_code, 200)
        eve = User.objects.get(email="eve@example.com")
        self.assertFalse(eve.is_superuser or eve.is_staff)
        self.assertEqual(self.client_for(eve).get("/api/master-admin/stats/").status_code, 403)

    def test_forged_token_rejected(self):
        token = str(self.client_for(self.owner)._credentials["HTTP_AUTHORIZATION"]).split()[1]
        header, payload, sig = token.split(".")
        import base64, json
        data = json.loads(base64.urlsafe_b64decode(payload + "=="))
        data["user_id"] = str(self.superadmin.id)
        data["is_superuser"] = True
        forged = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
        from rest_framework.test import APIClient
        attacker = APIClient()
        attacker.credentials(HTTP_AUTHORIZATION=f"Bearer {header}.{forged}.{sig}")
        self.assertEqual(attacker.get("/api/master-admin/stats/").status_code, 401)

    def test_platform_endpoints_refuse_everyone_else(self):
        for client in (self.client, self.client_for(self.owner), self.client_for(self.add_member("m@x.com"))):
            for path in ("stats/", "organisations/", "audit-logs/", f"organisations/{self.org.id}/"):
                self.assertIn(client.get(f"/api/master-admin/{path}").status_code, (401, 403), path)

    def test_create_superadmin_command_is_idempotent_and_never_promotes_silently(self):
        env = {"SUPERADMIN_EMAIL": "Boss@Example.com", "SUPERADMIN_PASSWORD": "Very-long-pass-2026"}
        with mock.patch.dict(os.environ, env):
            call_command("create_superadmin", stdout=StringIO())
            call_command("create_superadmin", stdout=StringIO())
        self.assertEqual(User.objects.filter(email__iexact="boss@example.com", is_superuser=True).count(), 1)
        with mock.patch.dict(os.environ, {"SUPERADMIN_EMAIL": self.owner.email, "SUPERADMIN_PASSWORD": "Very-long-pass-2026"}):
            with self.assertRaises(CommandError):
                call_command("create_superadmin", stdout=StringIO())
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.is_superuser)
        with mock.patch.dict(os.environ, {"SUPERADMIN_EMAIL": "x@example.com", "SUPERADMIN_PASSWORD": "123"}):
            with self.assertRaises(CommandError):
                call_command("create_superadmin", stdout=StringIO())

    def test_email_case_and_whitespace_cannot_create_duplicates(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="x", email="OWNER@example.com ", password="x-Strong-pass-1")


class IsolationTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.other_owner = self.make_user("boss@other.org")
        self.other = Organisation.objects.create(name="Other Org", slug="other-org", owner=self.other_owner, status="approved")
        OrganisationMember.objects.create(organisation=self.other, user=self.other_owner, role="owner")
        self.set_org(self.other_owner, self.other)
        self.outsider_member = OrganisationMember.objects.create(
            organisation=self.other, user=self.make_user("their.student@other.org"), role="candidate")
        self.other_invite = OrganisationInvite.objects.create(
            organisation=self.other, email="new@other.org", token="other-token", expires_at=now() + timedelta(days=1))

    def test_admin_cannot_touch_another_organisation(self):
        client = self.client_for(self.owner)
        slug = self.other.slug
        for path in (f"overview/", f"invites/", f"audit-logs/", f"members/", f"join-code/", f"devices/"):
            self.assertIn(client.get(f"/api/organisations/{slug}/{path}").status_code, (403, 404), path)
        self.assertIn(client.post(f"/api/organisations/{slug}/invites/{self.other_invite.id}/revoke/").status_code, (403, 404))
        self.assertIn(client.post(f"/api/organisations/{slug}/members/{self.outsider_member.id}/deactivate/").status_code, (403, 404))
        # Their own slug with the other organisation's object ids: not found.
        self.assertEqual(client.post(f"/api/organisations/{self.org.slug}/invites/{self.other_invite.id}/revoke/").status_code, 404)
        self.assertEqual(client.post(f"/api/organisations/{self.org.slug}/members/{self.outsider_member.id}/deactivate/").status_code, 404)
        self.other_invite.refresh_from_db()
        self.outsider_member.refresh_from_db()
        self.assertFalse(self.other_invite.is_revoked)
        self.assertTrue(self.outsider_member.is_active)

    def test_member_cannot_administer_and_loses_access_when_deactivated(self):
        student = self.add_member("student@example.com")
        client = self.client_for(student)
        self.assertEqual(client.get(f"/api/organisations/{self.org.slug}/overview/").status_code, 403)
        self.assertEqual(client.post("/api/admin/exam/create/", {}, format="json").status_code, 403)
        member = OrganisationMember.objects.get(user=student)
        self.assertEqual(self.client_for(self.owner).post(
            f"/api/organisations/{self.org.slug}/members/{member.id}/deactivate/").status_code, 200)
        self.assertEqual(client.get("/api/exams/").status_code, 403)

    def test_member_cannot_reach_other_organisations_exam(self):
        from exams.models import Exam
        exam = self.make_exam()
        Exam.objects.filter(pk=exam.pk).update(organisation=self.other)
        student = self.add_member("student@example.com")
        phone = self.approved_phone(student)
        client = self.client_for(student, phone)
        self.assertEqual(client.get(f"/api/exams/{exam.id}/").status_code, 404)
        self.assertEqual(client.post(f"/api/exams/{exam.id}/challenge/").status_code, 404)

    def test_owner_and_admin_rules_for_member_management(self):
        admin = self.add_member("admin@example.com", role="admin")
        other_admin = OrganisationMember.objects.create(
            organisation=self.org, user=self.make_user("admin2@example.com"), role="admin")
        owner_member = OrganisationMember.objects.get(user=self.owner)
        client = self.client_for(admin)
        self.assertEqual(client.post(f"/api/organisations/{self.org.slug}/members/{owner_member.id}/deactivate/").status_code, 403)
        self.assertEqual(client.post(f"/api/organisations/{self.org.slug}/members/{other_admin.id}/deactivate/").status_code, 403)


class InvitationTests(PlatformTestCase):
    def invite(self, email="invitee@example.com"):
        return self.client_for(self.owner).post(f"/api/organisations/{self.org.slug}/invite/", {"email": email}, format="json")

    def test_full_invitation_rules(self):
        token = self.invite().data["invite_token"]
        self.assertEqual(self.invite().data["status"], "invite already exists")
        self.assertEqual(OrganisationInvite.objects.filter(email="invitee@example.com").count(), 1)

        stranger = self.make_user("stranger@example.com")
        res = self.client_for(stranger).post("/api/organisations/join/", {"code": token}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.client_for(stranger).post("/api/organisations/join/", {"code": "guess"}, format="json").data["code"], "invalid_invite")

        invitee = self.make_user("invitee@example.com")
        client = self.client_for(invitee)
        self.assertEqual(client.post("/api/organisations/join/", {"code": token}, format="json").status_code, 200)
        self.assertEqual(client.post("/api/organisations/join/", {"code": token}, format="json").status_code, 400)
        self.assertEqual(OrganisationMember.objects.filter(user=invitee).count(), 1)

    def test_revoked_expired_declined_and_suspended(self):
        invitee = self.make_user("invitee@example.com")
        client = self.client_for(invitee)
        token = self.invite().data["invite_token"]
        invite = OrganisationInvite.objects.get(token=token)
        self.assertEqual(self.client_for(self.owner).post(
            f"/api/organisations/{self.org.slug}/invites/{invite.id}/revoke/").status_code, 200)
        self.assertEqual(client.post("/api/organisations/join/", {"code": token}, format="json").status_code, 400)

        invite2 = OrganisationInvite.objects.create(organisation=self.org, email="invitee@example.com", token="t2",
                                                    expires_at=now() - timedelta(minutes=1))
        self.assertEqual(client.post("/api/organisations/join/", {"code": invite2.token}, format="json").status_code, 400)

        token3 = self.invite().data["invite_token"]
        self.assertEqual(client.post("/api/organisations/invites/decline/", {"code": token3}, format="json").status_code, 200)
        self.assertEqual(client.post("/api/organisations/join/", {"code": token3}, format="json").status_code, 400)

        token4 = self.invite().data["invite_token"]
        self.act(self.org.id, "suspend", note="Review")
        self.assertEqual(client.post("/api/organisations/join/", {"code": token4}, format="json").status_code, 403)
        self.assertFalse(OrganisationMember.objects.filter(user=invitee).exists())

    def test_invite_list_statuses_and_existing_user_not_force_added(self):
        self.make_user("existing@example.com")
        self.invite("existing@example.com")
        self.assertFalse(OrganisationMember.objects.filter(user__email="existing@example.com").exists())
        data = self.client_for(self.owner).get(f"/api/organisations/{self.org.slug}/invites/?status=pending").data
        self.assertEqual([i["email"] for i in data["results"]], ["existing@example.com"])


class MeAndDashboardTests(PlatformTestCase):
    def test_me_reports_roles_from_server_data(self):
        me = self.super_client.get("/api/accounts/me/").data
        self.assertTrue(me["is_super_admin"])
        self.assertEqual(me["memberships"], [])
        me = self.client_for(self.owner).get("/api/accounts/me/").data
        self.assertFalse(me["is_super_admin"])
        self.assertEqual(me["memberships"][0]["role"], "owner")

    def test_stats_list_search_and_detail(self):
        self.apply(self.make_user("head@riverside.edu"))
        stats = self.super_client.get("/api/master-admin/stats/").data
        self.assertEqual(stats["organisations"]["pending"], 1)
        listing = self.super_client.get("/api/master-admin/organisations/?status=pending&search=river").data
        self.assertEqual(listing["count"], 1)
        detail = self.super_client.get(f"/api/master-admin/organisations/{listing['results'][0]['id']}/").data
        self.assertEqual(detail["owner"]["email"], "head@riverside.edu")
        self.assertEqual(detail["history"][0]["action"], "application_submitted")
        self.assertEqual(self.super_client.get("/api/master-admin/organisations/?page=999").status_code, 200)

    def test_org_overview_and_profile(self):
        client = self.client_for(self.owner)
        overview = client.get(f"/api/organisations/{self.org.slug}/overview/").data
        self.assertEqual(overview["your_role"], "owner")
        self.assertEqual(client.patch(f"/api/organisations/{self.org.slug}/profile/", {"name": "Renamed"}, format="json").status_code, 400)
        res = client.patch(f"/api/organisations/{self.org.slug}/profile/", {"website": "https://x.edu", "status": "approved"}, format="json")
        self.assertEqual(res.data["website"], "https://x.edu")


class AdminExamEndpointsTests(PlatformTestCase):
    def test_exam_admin_detail_includes_answers_for_admins_only(self):
        exam = self.make_exam()
        data = self.client_for(self.owner).get(f"/api/admin/exam/{exam.id}/").data
        self.assertFalse(data["has_attempts"])
        self.assertIn("is_correct", data["questions"][0]["options"][0])
        student = self.add_member("student@example.com")
        self.assertEqual(self.client_for(student).get(f"/api/admin/exam/{exam.id}/").status_code, 403)

    def test_results_and_members_carry_dashboard_fields(self):
        student = self.add_member("student@example.com")
        phone = self.approved_phone(student)
        exam = self.make_exam()
        self.start(self.client_for(student, phone), phone, exam)
        results = self.client_for(self.owner).get(f"/api/admin/exam/{exam.id}/results/").data
        self.assertEqual(results[0]["status"], "active")
        members = self.client_for(self.owner).get(f"/api/organisations/{self.org.slug}/members/").data
        self.assertIn("is_active", members[0])


class PlanManagementTests(PlatformTestCase):
    def test_only_super_admin_changes_plan_and_limits(self):
        url = f"/api/master-admin/organisations/{self.org.id}/plan/"
        self.assertEqual(self.client_for(self.owner).patch(url, {"plan": "enterprise"}, format="json").status_code, 403)
        self.assertEqual(self.super_client.patch(url, {"plan": "gold"}, format="json").status_code, 400)
        self.assertEqual(self.super_client.patch(url, {"max_exams": -1}, format="json").status_code, 400)
        res = self.super_client.patch(url, {"plan": "pro", "max_exams": 20}, format="json")
        self.assertEqual((res.data["plan"], res.data["limits"]["max_exams"]), ("pro", 20))
        self.assertTrue(AuditLog.objects.filter(action="organisation_plan_changed").exists())

    def test_overview_exposes_plan_features_and_unavailable_code(self):
        data = self.client_for(self.owner).get(f"/api/organisations/{self.org.slug}/overview/").data
        self.assertIn("allowed_question_types", data["features"])
        self.act(self.org.id, "suspend", note="x")
        res = self.client_for(self.owner).get("/api/admin/exam/list/")
        self.assertEqual(res.data["code"], "organisation_unavailable")
