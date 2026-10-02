"""Org-admin device approval and the invitee's pending-invite inbox."""

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.device_views import serialize_device
from accounts.models import UserDevice
from core.exceptions import api_error
from exams.models import ExamAttempt

from .models import Organisation, OrganisationInvite


def _admin_org(request, slug):
    org = get_object_or_404(Organisation, slug=slug, is_active=True)
    if not org.members.filter(
        user=request.user, is_active=True, role__in=["owner", "admin"]
    ).exists():
        return None
    return org


def _org_device(org, device_pk):
    """A device belonging to an active member of this org (no cross-org access)."""
    return get_object_or_404(
        UserDevice.objects.select_related("user"),
        pk=device_pk,
        user__memberships__organisation=org,
        user__memberships__is_active=True,
    )


class OrgDeviceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        org = _admin_org(request, slug)
        if org is None:
            return Response({"error": "Forbidden"}, status=403)
        status = request.query_params.get("status", UserDevice.STATUS_PENDING)
        devices = (
            UserDevice.objects.filter(
                user__memberships__organisation=org,
                user__memberships__is_active=True,
                status=status,
            )
            .select_related("user")
            .distinct()
            .order_by("-created_at")[:200]
        )
        return Response([
            {**serialize_device(d), "user_email": d.user.email, "user_name": d.user.name}
            for d in devices
        ])


class OrgDeviceDecisionView(APIView):
    """POST .../devices/<id>/approve/ or .../revoke/"""

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="user", rate="60/m", method="POST", block=True))
    def post(self, request, slug, device_pk, decision):
        if decision not in ("approve", "revoke"):
            return Response({"detail": "Not found."}, status=404)
        org = _admin_org(request, slug)
        if org is None:
            return Response({"error": "Forbidden"}, status=403)

        with transaction.atomic():
            device = _org_device(org, device_pk)
            device = UserDevice.objects.select_for_update().get(pk=device.pk)
            if ExamAttempt.objects.filter(user=device.user, status="active").exists():
                return api_error(
                    "device_change_during_exam",
                    "The candidate has an active exam; change devices afterwards",
                    409,
                )
            if decision == "approve":
                if device.status == UserDevice.STATUS_REVOKED:
                    return api_error("device_revoked", "A revoked device must re-register", 400)
                UserDevice.objects.filter(
                    user=device.user, status=UserDevice.STATUS_APPROVED
                ).exclude(pk=device.pk).update(status=UserDevice.STATUS_REVOKED)
                device.status = UserDevice.STATUS_APPROVED
                device.approved_by = request.user
                device.approved_at = now()
                device.pending_reason = ""
                device.save(update_fields=["status", "approved_by", "approved_at", "pending_reason"])
            else:
                device.status = UserDevice.STATUS_REVOKED
                device.save(update_fields=["status"])

        return Response(serialize_device(device))


class MyPendingInvitesView(APIView):
    """Invites for the caller's email that still need explicit acceptance."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        invites = (
            OrganisationInvite.objects.filter(
                email__iexact=request.user.email,
                accepted=False,
                is_revoked=False,
                organisation__is_active=True,
            )
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))
            .select_related("organisation")
            .order_by("-created_at")
        )
        return Response([
            {
                "token": invite.token,
                "org_name": invite.organisation.name,
                "org_slug": invite.organisation.slug,
                "role": invite.role,
                "expires_at": invite.expires_at,
            }
            for invite in invites
        ])
