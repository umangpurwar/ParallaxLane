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

    if not org.is_active:
        return None
    return org.members.filter(user=user, is_active=True).first()


class IsOrgMember(BasePermission):
    """User must belong to current organisation"""

    def has_permission(self, request, view):
        return get_membership(request.user) is not None


class IsOrgAdmin(BasePermission):
    """User must be admin or owner in current org"""

    def has_permission(self, request, view):
        membership = get_membership(request.user)
        if not membership:
            return False

        return membership.role in ["owner", "admin"]


class IsOrgInvigilator(BasePermission):
    """Owner, admin, or invigilator can access"""

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
    """Deployment-wide administrator; organisation roles are insufficient."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )
