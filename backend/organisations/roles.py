"""Organisation role constants and validation helpers."""

from .models import OrganisationMember

# Roles that may be assigned via invite API. Owner is never assignable through invites.
INVITABLE_ROLES = frozenset({
    OrganisationMember.ROLE_ADMIN,
    OrganisationMember.ROLE_INVIGILATOR,
    OrganisationMember.ROLE_CANDIDATE,
})

ALL_MEMBER_ROLES = frozenset({
    OrganisationMember.ROLE_OWNER,
    OrganisationMember.ROLE_ADMIN,
    OrganisationMember.ROLE_INVIGILATOR,
    OrganisationMember.ROLE_CANDIDATE,
})


def normalize_invite_role(role):
    """
    Return a safe invite role or None if the value is not allowed.
    Owner and unknown values are rejected.
    """
    if not role:
        return OrganisationMember.ROLE_CANDIDATE
    role = str(role).strip().lower()
    if role == OrganisationMember.ROLE_OWNER:
        return None
    if role in INVITABLE_ROLES:
        return role
    return None


def sanitize_stored_role(role):
    """Coerce persisted invite roles to a safe member role."""
    normalized = normalize_invite_role(role)
    return normalized or OrganisationMember.ROLE_CANDIDATE
