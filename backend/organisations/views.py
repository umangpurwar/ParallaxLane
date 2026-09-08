from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from .models import Organisation, OrganisationMember, OrganisationInvite
from .utils import role_capacity_available, sync_user_organisation_context
from .roles import normalize_invite_role, sanitize_stored_role
from .plan_usage import get_organisation_usage
from core.permissions import get_membership
from core.validators import normalize_email, validate_org_name
from core.email_service import EmailDeliveryError, send_invitation_email
from admin_panel.configuration import organisation_creation_enabled
from django.contrib.auth import get_user_model
import uuid
from django.utils.text import slugify
from django.utils.timezone import now
from datetime import timedelta
from rest_framework import serializers

User = get_user_model()


def _strict_bool(value):
    return serializers.BooleanField().run_validation(value)


def _active_org_for_slug(slug):
    return get_object_or_404(Organisation, slug=slug, is_active=True)


class CreateOrganisationView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="user", rate="3/m", method="POST", block=True))
    def post(self, request):
        if not organisation_creation_enabled():
            return Response(
                {"detail": "Organisation creation is currently disabled."},
                status=403,
            )

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
            organisation__is_active=True,
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
        try:
            with transaction.atomic():
                org = Organisation.objects.select_for_update().get(
                    slug=slug, is_active=True
                )

                if not org.members.filter(
                    user=request.user, is_active=True, role__in=["owner", "admin"]
                ).exists():
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

                existing_invite = OrganisationInvite.objects.select_for_update().filter(
                    organisation=org,
                    email=email,
                    accepted=False,
                    is_revoked=False,
                ).order_by("-created_at").first()
                if existing_invite and (
                    existing_invite.expires_at is None or existing_invite.expires_at > now()
                ):
                    return Response({
                        "status": "invite already exists",
                        "invite_token": existing_invite.token,
                        "expires_at": existing_invite.expires_at,
                    })

                user = User.objects.filter(email=email).first()
                member = OrganisationMember.objects.select_for_update().filter(
                    organisation=org, user=user
                ).first() if user else None

                # Existing active members do not consume another role slot.
                if not member or not member.is_active:
                    if not role_capacity_available(org, role):
                        limit = {
                            OrganisationMember.ROLE_ADMIN: org.max_admins,
                            OrganisationMember.ROLE_INVIGILATOR: org.max_invigilators,
                            OrganisationMember.ROLE_CANDIDATE: org.max_candidates,
                        }[role]
                        return Response({"error": f"{role.title()} limit reached (max {limit})"}, status=400)

                invite = OrganisationInvite.objects.create(
                    organisation=org, email=email, role=role,
                    token=str(uuid.uuid4()), expires_at=expires_at
                )

                if user:
                    if member is None:
                        member = OrganisationMember.objects.create(
                            organisation=org, user=user, role=role
                        )
                    elif not member.is_active:
                        member.role = role
                        member.is_active = True
                        member.save(update_fields=["role", "is_active"])
                    invite.accepted = True
                    invite.save(update_fields=["accepted"])
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

                send_invitation_email(
                    recipient=email,
                    organisation_name=org.name,
                    role=role,
                    invitation_code=invite.token,
                    expires_at=invite.expires_at,
                )

                return Response({"status": "invite created", "invite_token": invite.token, "expires_at": invite.expires_at})
        except Organisation.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        except EmailDeliveryError:
            return Response(
                {"error": "Invitation could not be delivered. Please try again."},
                status=503,
            )


class JoinByCodeView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='10/m', method='POST', block=True))
    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response({"error": "Join code required"}, status=400)
        
        code = code.strip().upper()
        org = get_object_or_404(Organisation, join_code=code, is_active=True)
        
        with transaction.atomic():
            # Get organisation with select_for_update to prevent race conditions
            org = Organisation.objects.select_for_update().get(pk=org.pk)
            if not org.is_join_code_valid():
                return Response({"error": "Invalid or expired join code"}, status=400)

            if org.members.filter(user=request.user).exists():
                return Response({"error": "Already a member of this organisation"}, status=400)

            active_members = org.members.filter(is_active=True)
            
            # Enforce candidate limit
            if active_members.filter(role=OrganisationMember.ROLE_CANDIDATE).count() >= org.max_candidates:
                return Response({"error": f"Candidate limit reached (max {org.max_candidates})"}, status=400)
            
            # Create membership
            member = OrganisationMember.objects.create(
                organisation=org, 
                user=request.user, 
                role=OrganisationMember.ROLE_CANDIDATE
            )
        
            # Set current organisation
            request.user.current_organisation = org
            request.user.save()
        
        return Response({
            "organisation_id": org.id,
            "organisation_name": org.name
        })


class OrganisationMembersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        org = _active_org_for_slug(slug)

        if not org.members.filter(
            user=request.user, is_active=True, role__in=["owner", "admin"]
        ).exists():
            return Response({"error": "Forbidden"}, status=403)

        members = org.members.select_related("user")
        data = [
            {
                "id": m.id,
                "username": m.user.username,
                "email": m.user.email,
                "role": m.role,
                "is_exam_enabled": m.is_exam_enabled
            } 
            for m in members
        ]
        return Response(data)


class ToggleMemberExamAccessView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def post(self, request, slug, member_id):
        org = _active_org_for_slug(slug)

        if not org.members.filter(
            user=request.user, is_active=True, role__in=["owner", "admin"]
        ).exists():
            return Response({"error": "Forbidden"}, status=403)
        
        member = get_object_or_404(OrganisationMember, pk=member_id, organisation=org)
        
        is_exam_enabled = request.data.get("is_exam_enabled")
        if is_exam_enabled is None:
            return Response({"error": "is_exam_enabled is required"}, status=400)
        
        try:
            is_exam_enabled = _strict_bool(is_exam_enabled)
        except serializers.ValidationError:
            return Response({"error": "is_exam_enabled must be a boolean"}, status=400)
        
        member.is_exam_enabled = is_exam_enabled
        member.save(update_fields=["is_exam_enabled"])
        
        return Response({
            "id": member.id,
            "is_exam_enabled": member.is_exam_enabled
        })


class OrganisationJoinCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        org = _active_org_for_slug(slug)

        if not org.members.filter(
            user=request.user, is_active=True, role__in=["owner", "admin"]
        ).exists():
            return Response({"error": "Forbidden"}, status=403)
        
        return Response({
            "join_code": org.join_code,
            "join_code_enabled": org.join_code_enabled,
            "join_code_valid_from": org.join_code_valid_from,
            "join_code_valid_until": org.join_code_valid_until
        })
    
    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def post(self, request, slug):
        org = _active_org_for_slug(slug)

        if not org.members.filter(
            user=request.user, is_active=True, role__in=["owner", "admin"]
        ).exists():
            return Response({"error": "Forbidden"}, status=403)
        
        join_code_enabled = request.data.get("join_code_enabled")
        join_code_valid_from = request.data.get("join_code_valid_from")
        join_code_valid_until = request.data.get("join_code_valid_until")
        regenerate_code = request.data.get("regenerate_code", False)
        
        if join_code_enabled is not None:
            try:
                org.join_code_enabled = _strict_bool(join_code_enabled)
            except serializers.ValidationError:
                return Response({"error": "join_code_enabled must be a boolean"}, status=400)
        if join_code_valid_from is not None:
            try:
                org.join_code_valid_from = serializers.DateTimeField().run_validation(
                    join_code_valid_from
                )
            except serializers.ValidationError:
                return Response({"error": "join_code_valid_from must be a valid datetime"}, status=400)
        if join_code_valid_until is not None:
            try:
                org.join_code_valid_until = serializers.DateTimeField().run_validation(
                    join_code_valid_until
                )
            except serializers.ValidationError:
                return Response({"error": "join_code_valid_until must be a valid datetime"}, status=400)
        if (
            org.join_code_valid_from
            and org.join_code_valid_until
            and org.join_code_valid_until < org.join_code_valid_from
        ):
            return Response(
                {"error": "join_code_valid_until must be after join_code_valid_from"},
                status=400,
            )
        if regenerate_code:
            org.regenerate_join_code()
        
        org.save(update_fields=[
            "join_code_enabled", 
            "join_code_valid_from", 
            "join_code_valid_until",
            "join_code"
        ])
        
        return Response({
            "join_code": org.join_code,
            "join_code_enabled": org.join_code_enabled,
            "join_code_valid_from": org.join_code_valid_from,
            "join_code_valid_until": org.join_code_valid_until
        })


def _accept_invite_for_user(user, token):
    with transaction.atomic():
        invite = get_object_or_404(
            OrganisationInvite.objects.select_for_update(), token=token
        )
        org = Organisation.objects.select_for_update().get(pk=invite.organisation_id)

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

        if not org.is_active:
            return None, Response({"error": "Organisation is inactive"}, status=403)

        member = OrganisationMember.objects.select_for_update().filter(
            organisation=org, user=user
        ).first()
        if member and member.is_active:
            invite.accepted = True
            invite.save(update_fields=["accepted"])
        else:
            if not role_capacity_available(
                org, safe_role, exclude_invite_id=invite.id, include_pending=False
            ):
                limit = {
                    OrganisationMember.ROLE_ADMIN: org.max_admins,
                    OrganisationMember.ROLE_INVIGILATOR: org.max_invigilators,
                    OrganisationMember.ROLE_CANDIDATE: org.max_candidates,
                }[safe_role]
                return None, Response({"error": f"{safe_role.title()} limit reached (max {limit})"}, status=400)

            if member is None:
                member = OrganisationMember.objects.create(
                    organisation=org, user=user, role=safe_role
                )
            else:
                member.role = safe_role
                member.is_active = True
                member.save(update_fields=["role", "is_active"])

            invite.accepted = True
            invite.save(update_fields=["accepted"])

        user.current_organisation = org
        user.save(update_fields=["current_organisation"])

        return {
            "status": "joined",
            "slug": org.slug,
            "name": org.name,
            "plan": org.plan,
            "role": member.role,
            "org_slug": org.slug,
            "org_name": org.name,
            "org_plan": org.plan,
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
            **usage,
        })
