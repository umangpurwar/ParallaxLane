from django.utils.timezone import now

from .models import OrganisationInvite, OrganisationMember
from .roles import sanitize_stored_role


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

    for invite in pending_invites:
        if invite.expires_at and now() > invite.expires_at:
            continue

        safe_role = sanitize_stored_role(invite.role)
        OrganisationMember.objects.get_or_create(
            organisation=invite.organisation,
            user=user,
            defaults={"role": safe_role},
        )
        invite.accepted = True
        invite.save(update_fields=["accepted"])

        if not user.current_organisation_id:
            user.current_organisation = invite.organisation
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
