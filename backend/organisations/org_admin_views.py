"""Organisation admin endpoints used by the admin dashboard.

Every view resolves the organisation from the URL slug and then checks that
the caller is an active owner/admin of that approved organisation. Client
supplied organisation ids are never trusted.
"""

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserDevice
from admin_panel.audit import audit, serialize_log
from admin_panel.models import AuditLog
from core.pagination import paginate
from exams.models import Exam, ExamAttempt

from .application_views import serialize_application
from .models import Organisation, OrganisationInvite, OrganisationMember
from .services import ApplicationError, _clean_details


def _admin_context(request, slug, lock=False):
    """(org, membership) for an owner/admin of an approved org, else (None, None)."""
    qs = Organisation.objects.select_for_update() if lock else Organisation.objects
    org = qs.filter(slug=slug, is_active=True).first()
    if org is None or request.user.is_superuser or request.user.is_staff:
        return None, None
    membership = org.members.filter(
        user=request.user, is_active=True, role__in=["owner", "admin"]
    ).first()
    if membership is None:
        return None, None
    return org, membership


def _forbidden():
    return Response(
        {"error": "You do not administer an approved organisation with this address.", "code": "forbidden"},
        status=403,
    )


def invite_status(invite):
    if invite.accepted:
        return "accepted"
    if invite.declined:
        return "declined"
    if invite.is_revoked:
        return "revoked"
    if invite.expires_at and invite.expires_at <= now():
        return "expired"
    return "pending"


def serialize_invite(invite):
    return {
        "id": invite.id,
        "email": invite.email,
        "role": invite.role,
        "status": invite_status(invite),
        "created_at": invite.created_at,
        "expires_at": invite.expires_at,
    }


class OrgOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        org, membership = _admin_context(request, slug)
        if org is None:
            return _forbidden()
        roles = dict(
            org.members.filter(is_active=True).values_list("role").annotate(n=Count("id")).values_list("role", "n")
        )
        exams = Exam.objects.filter(organisation=org)
        return Response({
            "organisation": serialize_application(org),
            "plan": org.plan,
            "your_role": membership.role,
            "members": {"total": sum(roles.values()), "by_role": roles},
            "exams": {
                "total": exams.count(),
                "published": exams.filter(is_published=True).count(),
                "active": exams.filter(is_active=True, start_time__lte=now(), end_time__gte=now()).count(),
            },
            "active_attempts": ExamAttempt.objects.filter(exam__organisation=org, status="active").count(),
            "pending_invites": OrganisationInvite.objects.filter(
                organisation=org, accepted=False, declined=False, is_revoked=False
            ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now())).count(),
            "pending_devices": UserDevice.objects.filter(
                status=UserDevice.STATUS_PENDING, user__memberships__organisation=org,
                user__memberships__is_active=True,
            ).distinct().count(),
            "limits": {
                "max_exams": org.max_exams, "max_candidates": org.max_candidates,
                "max_admins": org.max_admins, "max_invigilators": org.max_invigilators,
            },
        })


class OrgProfileView(APIView):
    """Owner/admin edit contact details. The name is fixed once approved."""

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="user", rate="20/m", method="PATCH", block=True))
    def patch(self, request, slug):
        if "name" in request.data:
            return Response({"error": "The organisation name cannot be changed after approval.", "code": "invalid_request"}, status=400)
        with transaction.atomic():
            org, _ = _admin_context(request, slug, lock=True)
            if org is None:
                return _forbidden()
            try:
                details = _clean_details(request.data, require_name=False)
            except ApplicationError as exc:
                return Response({"error": exc.message, "code": exc.code}, status=exc.status)
            for field, value in details.items():
                setattr(org, field, value)
            org.save(update_fields=list(details) or None)
            audit(request.user, "organisation_profile_updated", org, fields=sorted(details))
        return Response(serialize_application(org))


class OrgInvitesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        org, _ = _admin_context(request, slug)
        if org is None:
            return _forbidden()
        invites = OrganisationInvite.objects.filter(organisation=org).order_by("-created_at")
        wanted = request.query_params.get("status")
        search = (request.query_params.get("search") or "").strip()
        if search:
            invites = invites.filter(email__icontains=search)
        if wanted:
            invites = [i for i in invites if invite_status(i) == wanted]
        return Response(paginate(request, invites, serialize_invite))


class RevokeInviteView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="user", rate="60/m", method="POST", block=True))
    def post(self, request, slug, invite_id):
        with transaction.atomic():
            org, _ = _admin_context(request, slug)
            if org is None:
                return _forbidden()
            invite = get_object_or_404(
                OrganisationInvite.objects.select_for_update(), pk=invite_id, organisation=org
            )
            if invite_status(invite) != "pending":
                return Response({"error": f"Invite is {invite_status(invite)}, not pending", "code": "invalid_state"}, status=409)
            invite.is_revoked = True
            invite.save(update_fields=["is_revoked"])
            audit(request.user, "invite_revoked", org, target=invite.email)
        return Response(serialize_invite(invite))


class DeclineInviteView(APIView):
    """The invitee declines an invitation addressed to their own email."""

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="user", rate="20/m", method="POST", block=True))
    def post(self, request):
        token = str(request.data.get("code") or "").strip()
        with transaction.atomic():
            invite = OrganisationInvite.objects.select_for_update().filter(token=token).first()
            if invite is None or invite.email.lower() != request.user.email.lower():
                return Response({"error": "Invalid invite", "code": "invalid_invite"}, status=400)
            if invite_status(invite) != "pending":
                return Response({"error": f"Invite is {invite_status(invite)}", "code": "invalid_state"}, status=409)
            invite.declined = True
            invite.save(update_fields=["declined"])
            audit(request.user, "invite_declined", invite.organisation, target=invite.email)
        return Response({"status": "declined"})


class MemberActiveView(APIView):
    """POST .../members/<id>/deactivate/ or .../activate/"""

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="user", rate="60/m", method="POST", block=True))
    def post(self, request, slug, member_id, action):
        if action not in ("activate", "deactivate"):
            return Response({"detail": "Not found."}, status=404)
        with transaction.atomic():
            org, actor = _admin_context(request, slug, lock=True)
            if org is None:
                return _forbidden()
            member = get_object_or_404(
                OrganisationMember.objects.select_for_update().select_related("user"), pk=member_id, organisation=org
            )
            if member.role == OrganisationMember.ROLE_OWNER:
                return Response({"error": "The owner cannot be deactivated", "code": "forbidden"}, status=403)
            if member.pk == actor.pk:
                return Response({"error": "You cannot change your own membership", "code": "forbidden"}, status=403)
            if member.role == OrganisationMember.ROLE_ADMIN and actor.role != OrganisationMember.ROLE_OWNER:
                return Response({"error": "Only the owner can change admins", "code": "forbidden"}, status=403)
            member.is_active = action == "activate"
            member.save(update_fields=["is_active"])
            audit(request.user, f"member_{action}d", org, target=member.user.email, role=member.role)
        return Response({"id": member.id, "is_active": member.is_active})


class OrgAuditLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        org, _ = _admin_context(request, slug)
        if org is None:
            return _forbidden()
        logs = AuditLog.objects.filter(organisation=org).select_related("actor", "organisation")
        action = request.query_params.get("action")
        if action:
            logs = logs.filter(action=action)
        return Response(paginate(request, logs, serialize_log))
