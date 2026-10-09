"""Super admin (platform) endpoints. Every view requires a Django superuser."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django_ratelimit.decorators import ratelimit
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import paginate
from core.permissions import IsMasterAdmin
from exams.models import Exam, ExamAttempt
from organisations.models import Organisation
from organisations.services import ApplicationError, review_organisation

from .audit import serialize_log
from .configuration import organisation_creation_enabled, set_organisation_creation_enabled
from .models import AuditLog

User = get_user_model()
ORDERINGS = {"newest": "-submitted_at", "oldest": "submitted_at", "name": "name"}


def _annotated():
    return Organisation.objects.select_related("owner", "reviewed_by").annotate(
        member_count=Count("members", filter=Q(members__is_active=True), distinct=True),
        exam_count=Count("exams", distinct=True),
    )


def _organisation_summary(org):
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "status": org.status,
        "plan": org.plan,
        "owner": {"id": org.owner_id, "name": org.owner.name, "email": org.owner.email},
        "member_count": org.member_count,
        "exam_count": org.exam_count,
        "submitted_at": org.submitted_at,
        "created_at": org.created_at,
    }


def _organisation_detail(org):
    data = _organisation_summary(org)
    data.update({
        "description": org.description,
        "contact_phone": org.contact_phone,
        "website": org.website,
        "review_note": org.review_note,
        "reviewed_by": org.reviewed_by.email if org.reviewed_by_id else None,
        "reviewed_at": org.reviewed_at,
        "limits": {
            "max_exams": org.max_exams, "max_candidates": org.max_candidates,
            "max_admins": org.max_admins, "max_invigilators": org.max_invigilators,
        },
        "history": [
            serialize_log(entry)
            for entry in AuditLog.objects.filter(organisation=org).select_related("actor", "organisation")[:50]
        ],
    })
    return data


class MasterAdminStatusView(APIView):
    permission_classes = [IsMasterAdmin]

    def get(self, request):
        return Response({"organisation_creation_enabled": organisation_creation_enabled()})


class MasterAdminStatsView(APIView):
    permission_classes = [IsMasterAdmin]

    def get(self, request):
        by_status = dict(
            Organisation.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n")
        )
        week_ago = now() - timedelta(days=7)
        return Response({
            "organisations": {status: by_status.get(status, 0) for status, _ in Organisation.STATUS_CHOICES},
            "users": User.objects.filter(is_active=True, is_superuser=False).count(),
            "exams": Exam.objects.count(),
            "attempts_last_7_days": ExamAttempt.objects.filter(start_time__gte=week_ago).count(),
            "active_attempts": ExamAttempt.objects.filter(status="active").count(),
            "organisation_creation_enabled": organisation_creation_enabled(),
        })


class MasterAdminOrganisationListView(APIView):
    permission_classes = [IsMasterAdmin]

    def get(self, request):
        orgs = _annotated()
        status = request.query_params.get("status")
        if status in dict(Organisation.STATUS_CHOICES):
            orgs = orgs.filter(status=status)
        search = (request.query_params.get("search") or "").strip()
        if search:
            orgs = orgs.filter(Q(name__icontains=search) | Q(owner__email__icontains=search) | Q(slug__icontains=search))
        orgs = orgs.order_by(ORDERINGS.get(request.query_params.get("ordering"), "-submitted_at"), "id")
        return Response(paginate(request, orgs, _organisation_summary))


class MasterAdminOrganisationDetailView(APIView):
    permission_classes = [IsMasterAdmin]

    def get(self, request, organisation_id):
        return Response(_organisation_detail(get_object_or_404(_annotated(), id=organisation_id)))


class MasterAdminOrganisationActionView(APIView):
    """POST organisations/<id>/<approve|reject|suspend|reactivate>/ with optional {note}."""

    permission_classes = [IsMasterAdmin]

    @method_decorator(ratelimit(key="user", rate="60/m", method="POST", block=True))
    def post(self, request, organisation_id, action):
        if action not in ("approve", "reject", "suspend", "reactivate"):
            return Response({"detail": "Not found."}, status=404)
        try:
            review_organisation(organisation_id, action, request.user, request.data.get("note", ""))
        except ApplicationError as exc:
            return Response({"error": exc.message, "code": exc.code}, status=exc.status)
        return Response(_organisation_detail(_annotated().get(id=organisation_id)))


class MasterAdminAuditLogView(APIView):
    permission_classes = [IsMasterAdmin]

    def get(self, request):
        logs = AuditLog.objects.select_related("actor", "organisation")
        if request.query_params.get("organisation"):
            logs = logs.filter(organisation_id=request.query_params.get("organisation"))
        if request.query_params.get("action"):
            logs = logs.filter(action=request.query_params.get("action"))
        search = (request.query_params.get("search") or "").strip()
        if search:
            logs = logs.filter(Q(target__icontains=search) | Q(actor__email__icontains=search) | Q(organisation__name__icontains=search))
        return Response(paginate(request, logs, serialize_log))


class MasterAdminOrganisationCreationSettingView(APIView):
    permission_classes = [IsMasterAdmin]

    def get(self, request):
        return Response({"organisation_creation_enabled": organisation_creation_enabled()})

    def patch(self, request):
        try:
            value = serializers.BooleanField().run_validation(request.data.get("organisation_creation_enabled"))
        except serializers.ValidationError:
            return Response({"error": "organisation_creation_enabled must be a boolean.", "code": "invalid_request"}, status=400)
        setting = set_organisation_creation_enabled(value, request.user)
        from .audit import audit
        audit(request.user, "applications_toggled", None, enabled=setting.boolean_value)
        return Response({"organisation_creation_enabled": setting.boolean_value})
