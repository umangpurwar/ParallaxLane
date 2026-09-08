from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsMasterAdmin
from organisations.models import Organisation

from .configuration import (
    organisation_creation_enabled,
    set_organisation_creation_enabled,
)


class MasterAdminStatusView(APIView):
    permission_classes = [IsMasterAdmin]

    def get(self, request):
        return Response({
            "organisation_creation_enabled": organisation_creation_enabled(),
            "organisation_creation_control": "database_override_or_environment_default",
        })


def _organisation_summary(organisation):
    return {
        "id": organisation.id,
        "name": organisation.name,
        "slug": organisation.slug,
        "is_active": organisation.is_active,
        "owner": {
            "id": organisation.owner_id,
            "name": organisation.owner.name,
        },
        "member_count": organisation.member_count,
        "exam_count": organisation.exam_count,
        "created_at": organisation.created_at,
    }


class MasterAdminOrganisationListView(APIView):
    permission_classes = [IsMasterAdmin]

    def get(self, request):
        organisations = (
            Organisation.objects.select_related("owner")
            .annotate(
                member_count=Count("members", distinct=True),
                exam_count=Count("exams", distinct=True),
            )
            .order_by("id")
        )
        return Response([_organisation_summary(organisation) for organisation in organisations])


class MasterAdminOrganisationDetailView(APIView):
    permission_classes = [IsMasterAdmin]

    def get(self, request, organisation_id):
        organisation = get_object_or_404(
            Organisation.objects.select_related("owner").annotate(
                member_count=Count("members", distinct=True),
                exam_count=Count("exams", distinct=True),
            ),
            id=organisation_id,
        )
        return Response(_organisation_summary(organisation))


class MasterAdminOrganisationCreationSettingView(APIView):
    permission_classes = [IsMasterAdmin]

    def get(self, request):
        return Response({
            "organisation_creation_enabled": organisation_creation_enabled(),
        })

    def patch(self, request):
        value = request.data.get("organisation_creation_enabled")
        try:
            value = serializers.BooleanField().run_validation(value)
        except serializers.ValidationError:
            return Response(
                {"detail": "organisation_creation_enabled must be a boolean."},
                status=400,
            )
        setting = set_organisation_creation_enabled(value, request.user)
        return Response({
            "organisation_creation_enabled": setting.boolean_value,
        })
