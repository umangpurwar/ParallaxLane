from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from .models import Organisation, OrganisationMember, OrganisationInvite, Coupon
from .utils import sync_user_organisation_context
from .roles import normalize_invite_role, sanitize_stored_role
from .plan_usage import get_organisation_usage
from core.permissions import get_membership
from core.validators import normalize_email, validate_org_name
from django.contrib.auth import get_user_model
import uuid
from django.utils.text import slugify
from django.utils.timezone import now
from datetime import timedelta

User = get_user_model()


class CreateOrganisationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            name = validate_org_name(request.data.get("name"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)

        base_slug = slugify(name)
        slug = base_slug
        counter = 1

        while Organisation.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organisation.objects.create(name=name, slug=slug, owner=request.user)

        OrganisationMember.objects.create(organisation=org, user=request.user, role="owner")

        request.user.current_organisation = org
        request.user.save()

        return Response({"status": "created", "slug": org.slug, "name": org.name, "plan": org.plan, "role": "owner"})


class MyOrganisationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            OrganisationMember.objects
            .filter(user=request.user, is_active=True)
            .select_related("organisation")
        )

        data = [
            {
                "name": m.organisation.name,
                "slug": m.organisation.slug,
                "role": m.role,
                "plan": m.organisation.plan,
            }
            for m in memberships
        ]

        return Response({"count": len(data), "organisations": data})


class SwitchOrganisationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        membership = OrganisationMember.objects.filter(
            user=request.user,
            organisation__slug=slug,
            is_active=True,
        ).first()

        if not membership:
            return Response({"error": "Not a member"}, status=403)

        request.user.current_organisation = membership.organisation
        request.user.save()

        return Response({
            "status": "switched",
            "slug": membership.organisation.slug,
            "name": membership.organisation.name,
            "plan": membership.organisation.plan,
            "org_plan": membership.organisation.plan,
            "org_slug": membership.organisation.slug,
            "org_name": membership.organisation.name,
            "role": membership.role,
            "org_role": membership.role,
        })


class InviteMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        org = get_object_or_404(Organisation, slug=slug)

        if not org.members.filter(user=request.user, role__in=["owner", "admin"]).exists():
            return Response({"error": "Forbidden"}, status=403)

        try:
            email = normalize_email(request.data.get("email"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)

        role = normalize_invite_role(request.data.get("role", "candidate"))
        expiry_days = request.data.get("expiry_days")

        if role is None:
            return Response(
                {"error": "Invalid role. Allowed: admin, invigilator, candidate"},
                status=400,
            )

        expires_at = None
        if expiry_days:
            try:
                expiry_days = int(expiry_days)
                if expiry_days < 1 or expiry_days > 30:
                    return Response({"error": "expiry_days must be between 1 and 30"}, status=400)
                expires_at = now() + timedelta(days=expiry_days)
            except (ValueError, TypeError):
                return Response({"error": "Invalid expiry_days"}, status=400)

        invite = OrganisationInvite.objects.create(
            organisation=org, email=email, role=role,
            token=str(uuid.uuid4()), expires_at=expires_at
        )

        user = User.objects.filter(email=email).first()

        if user:
            member, _ = OrganisationMember.objects.get_or_create(
                organisation=org, user=user, defaults={"role": role}
            )
            invite.accepted = True
            invite.save()
            if not user.current_organisation_id:
                user.current_organisation = org
                user.save(update_fields=["current_organisation"])
            return Response({
                "status": "user added directly",
                "org_slug": org.slug,
                "org_name": org.name,
                "org_plan": org.plan,
                "org_role": member.role
            })

        return Response({"status": "invite created", "invite_token": invite.token, "expires_at": invite.expires_at})


class OrganisationMembersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        org = get_object_or_404(Organisation, slug=slug)

        if not org.members.filter(user=request.user, role__in=["owner", "admin"]).exists():
            return Response({"error": "Forbidden"}, status=403)

        members = org.members.select_related("user")
        data = [{"username": m.user.username, "email": m.user.email, "role": m.role} for m in members]
        return Response(data)


def _accept_invite_for_user(user, token):
    invite = get_object_or_404(OrganisationInvite, token=token)

    if invite.accepted:
        return None, Response({"error": "Already accepted"}, status=400)

    if invite.is_revoked:
        return None, Response({"error": "Invite revoked"}, status=400)

    if invite.expires_at and now() > invite.expires_at:
        return None, Response({"error": "Invite expired"}, status=400)

    if user.email.lower().strip() != invite.email.lower().strip():
        return None, Response(
            {"error": "This invite was issued for a different email address"},
            status=403,
        )

    safe_role = sanitize_stored_role(invite.role)

    member, _ = OrganisationMember.objects.get_or_create(
        organisation=invite.organisation, user=user, defaults={"role": safe_role}
    )

    invite.accepted = True
    invite.save()

    user.current_organisation = invite.organisation
    user.save()

    return {
        "status": "joined",
        "slug": invite.organisation.slug,
        "name": invite.organisation.name,
        "plan": invite.organisation.plan,
        "role": member.role,
        "org_slug": invite.organisation.slug,
        "org_name": invite.organisation.name,
        "org_plan": invite.organisation.plan,
        "org_role": member.role,
    }, None


class JoinOrganisationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response({"error": "Invite code required"}, status=400)

        result, error_response = _accept_invite_for_user(request.user, code.strip())
        if error_response:
            return error_response
        return Response(result)


class AcceptInviteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        result, error_response = _accept_invite_for_user(request.user, token)
        if error_response:
            return error_response
        return Response(result)


def _require_org_admin(request):
    membership = get_membership(request.user)
    if not membership:
        return None, Response({"error": "No active organisation selected"}, status=403)
    if membership.role not in [OrganisationMember.ROLE_OWNER, OrganisationMember.ROLE_ADMIN]:
        return None, Response({"error": "Only organisation owners and admins can manage plans"}, status=403)
    return membership, None


class OrganisationSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        membership = get_membership(request.user)
        if not membership:
            return Response({"error": "No active organisation selected"}, status=403)

        org = membership.organisation
        usage = get_organisation_usage(org)

        return Response({
            "organisation": {
                "name": org.name,
                "slug": org.slug,
                "plan": org.plan,
                "plan_label": org.plan.upper(),
            },
            "role": membership.role,
            "can_redeem_coupons": membership.role in [
                OrganisationMember.ROLE_OWNER,
                OrganisationMember.ROLE_ADMIN,
            ],
            **usage,
        })


class RedeemCouponView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def post(self, request):
        membership, error = _require_org_admin(request)
        if error:
            return error

        code = (request.data.get("code") or "").strip().upper()
        if not code:
            return Response({"error": "Coupon code is required"}, status=400)

        with transaction.atomic():
            try:
                coupon = Coupon.objects.select_for_update().get(code=code)
            except Coupon.DoesNotExist:
                return Response({"error": "Invalid coupon code"}, status=400)

            if not coupon.active:
                return Response({"error": "This coupon is no longer active"}, status=400)

            if coupon.is_expired:
                return Response({"error": "This coupon has expired"}, status=400)

            if coupon.is_exhausted:
                return Response({"error": "This coupon has reached its usage limit"}, status=400)

            org = membership.organisation
            org.plan = coupon.plan
            org.save(update_fields=["plan"])

            Coupon.objects.filter(pk=coupon.pk).update(used_count=F("used_count") + 1)
            coupon.refresh_from_db()

        usage = get_organisation_usage(org)

        return Response({
            "status": "redeemed",
            "message": f"Plan upgraded to {org.plan.upper()}",
            "plan": org.plan,
            "plan_label": org.plan.upper(),
            "org_plan": org.plan,
            "org_name": org.name,
            "org_slug": org.slug,
            "coupon_code": coupon.code,
            **usage,
        })