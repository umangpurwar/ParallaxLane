"""GET accounts/me/: who the caller is, as the admin dashboard needs to know it."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organisations.application_views import serialize_application
from organisations.models import Organisation, OrganisationMember


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = bool(user.is_superuser)
        memberships = [] if is_super else [
            {
                "slug": m.organisation.slug,
                "name": m.organisation.name,
                "role": m.role,
                "status": m.organisation.status,
                "is_admin": m.role in (OrganisationMember.ROLE_OWNER, OrganisationMember.ROLE_ADMIN),
            }
            for m in OrganisationMember.objects.filter(user=user, is_active=True).select_related("organisation")
        ]
        applications = [] if is_super else [
            serialize_application(org) for org in Organisation.objects.filter(owner=user).order_by("-submitted_at")
        ]
        return Response({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_super_admin": is_super,
            "current_organisation": user.current_organisation.slug if user.current_organisation_id else None,
            "memberships": memberships,
            "applications": applications,
        })
