from rest_framework.permissions import BasePermission


def get_membership(user):
    """
    Returns the active membership of the user in current organisation.
    """
    if not user or not user.is_authenticated:
        return None

    org = getattr(user, "current_organisation", None)
    if not org:
        return None

    # is_active on an organisation is true only while it is approved.
    if not org.is_active or user.is_superuser or user.is_staff:
        return None
    return org.members.filter(user=user, is_active=True).first()


ORG_UNAVAILABLE = {
    "error": "You are not an active member of an approved organisation.",
    "code": "organisation_unavailable",
}
ORG_ROLE_REQUIRED = {
    "error": "Your role in this organisation does not allow this action.",
    "code": "forbidden",
}


class IsOrgMember(BasePermission):
    """User must belong to current organisation"""

    message = ORG_UNAVAILABLE

    def has_permission(self, request, view):
        return get_membership(request.user) is not None


class IsOrgAdmin(BasePermission):
    """User must be admin or owner in current org"""

    message = ORG_ROLE_REQUIRED

    def has_permission(self, request, view):
        membership = get_membership(request.user)
        if not membership:
            return False

        return membership.role in ["owner", "admin"]


class IsOrgInvigilator(BasePermission):
    """Owner, admin, or invigilator can access"""

    message = ORG_ROLE_REQUIRED

    def has_permission(self, request, view):
        membership = get_membership(request.user)
        if not membership:
            return False

        return membership.role in ["owner", "admin", "invigilator"]


class IsSuperAdmin(BasePermission):
    """Backward-compatible alias for the platform-level permission."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsMasterAdmin(BasePermission):
    """Deployment-wide administrator (Django superuser, provisioned only by the
    create_superadmin command). Organisation roles are never sufficient."""

    message = {"error": "Super admin access required.", "code": "forbidden"}

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )
