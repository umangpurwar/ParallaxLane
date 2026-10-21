from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now

from .models import Organisation, OrganisationInvite, OrganisationMember
from .roles import sanitize_stored_role


def sync_user_organisation_context(user):
    """
    Accept pending invites for the user's email, ensure current_organisation is set,
    and return org fields for auth responses.
    """
    email = user.email.lower().strip()
    if user.is_superuser or user.is_staff:
        # Platform accounts never join organisations.
        return {"org_slug": None, "org_name": None, "org_role": None}

    pending_invites = OrganisationInvite.objects.filter(
        email__iexact=email,
        accepted=False,
        is_revoked=False,
        declined=False,
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
            # Invites sent after the account existed need explicit acceptance
            # (organisations/join/ or organisations/invites/); auto-joining
            # would let any org admin pull an existing user in.
            if invite.created_at > user.date_joined:
                continue

            safe_role = sanitize_stored_role(invite.role)
            member = OrganisationMember.objects.select_for_update().filter(
                organisation=org, user=user
            ).first()
            if member and member.is_active:
                invite.accepted = True
                invite.save(update_fields=["accepted"])
            else:
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
        "org_role": membership.role if membership else None,
    }
