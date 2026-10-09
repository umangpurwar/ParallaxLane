"""The applicant's side of organisation registration."""

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Organisation
from .services import ApplicationError, update_application


def serialize_application(org):
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "description": org.description,
        "contact_phone": org.contact_phone,
        "website": org.website,
        "status": org.status,
        "review_note": org.review_note if org.status in ("rejected", "suspended") else "",
        "submitted_at": org.submitted_at,
        "reviewed_at": org.reviewed_at,
    }


def _error(exc):
    return Response({"error": exc.message, "code": exc.code}, status=exc.status)


class MyApplicationsView(APIView):
    """Organisations the caller registered, with their review status."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        orgs = Organisation.objects.filter(owner=request.user).order_by("-submitted_at")
        return Response([serialize_application(org) for org in orgs])


class ApplicationDetailView(APIView):
    """PATCH edits a pending application (owner only)."""

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="user", rate="10/m", method="PATCH", block=True))
    def patch(self, request, org_id):
        try:
            org = update_application(request.user, org_id, request.data)
        except ApplicationError as exc:
            return _error(exc)
        return Response(serialize_application(org))


class ResubmitApplicationView(APIView):
    """POST sends a rejected application back for review, with edits."""

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="user", rate="3/m", method="POST", block=True))
    def post(self, request, org_id):
        try:
            org = update_application(request.user, org_id, request.data, resubmit=True)
        except ApplicationError as exc:
            return _error(exc)
        return Response(serialize_application(org))
