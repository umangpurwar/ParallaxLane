from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now

from .models import Organisation, OrganisationInvite, OrganisationMember
from .roles import sanitize_stored_role


def role_capacity_available(org, role, exclude_invite_id=None, include_pending=True):
    """Check a role limit using committed active memberships."""
    active_members = org.members.filter(is_active=True, role=role).count()
    if role == OrganisationMember.ROLE_ADMIN:
        limit = org.max_admins
    elif role == OrganisationMember.ROLE_INVIGILATOR:
        limit = org.max_invigilators
    elif role == OrganisationMember.ROLE_CANDIDATE:
        limit = org.max_candidates
    else:
        return True

    # Pending invitations reserve capacity at creation time. During acceptance
    # or auto-acceptance, the current invitation is the slot being consumed.
    reserved_slots = active_members
    if include_pending:
        pending_invites = OrganisationInvite.objects.filter(
            organisation=org,
            role=role,
            accepted=False,
            is_revoked=False,
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now()))
        if exclude_invite_id is not None:
            pending_invites = pending_invites.exclude(id=exclude_invite_id)
        reserved_slots += pending_invites.count()

    return reserved_slots < limit


def sync_user_organisation_context(user):
    """
    Accept pending invites for the user's email, ensure current_organisation is set,
    and return org fields for auth responses.
    """
    email = user.email.lower().strip()

    pending_invites = OrganisationInvite.objects.filter(
        email__iexact=email,
        accepted=False,
        is_revoked=False,
    ).order_by("-created_at")

    for pending_invite in pending_invites:
        with transaction.atomic():
            invite = OrganisationInvite.objects.select_for_update().get(
                pk=pending_invite.pk
            )
            org = Organisation.objects.select_for_update().get(
                pk=invite.organisation_id
            )
            if invite.accepted or invite.is_revoked:
                continue
            if invite.expires_at and now() > invite.expires_at:
                continue
            if not org.is_active:
                continue

            safe_role = sanitize_stored_role(invite.role)
            member = OrganisationMember.objects.select_for_update().filter(
                organisation=org, user=user
            ).first()
            if member and member.is_active:
                invite.accepted = True
                invite.save(update_fields=["accepted"])
            else:
                if not role_capacity_available(
                    org, safe_role, exclude_invite_id=invite.id
                ):
                    continue
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

            if not user.current_organisation_id:
                user.current_organisation = org
                user.save(update_fields=["current_organisation"])

    if not user.current_organisation_id:
        membership = (
            OrganisationMember.objects.filter(user=user, is_active=True)
            .select_related("organisation")
            .first()
        )
        if membership:
            user.current_organisation = membership.organisation
            user.save(update_fields=["current_organisation"])

    org = user.current_organisation
    if not org:
        return {}

    membership = org.members.filter(user=user, is_active=True).first()
    return {
        "org_slug": org.slug,
        "org_name": org.name,
        "org_plan": org.plan,
        "org_role": membership.role if membership else None,
    }
