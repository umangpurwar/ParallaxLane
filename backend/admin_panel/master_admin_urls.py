from django.urls import path

from .master_admin_views import (
    MasterAdminAuditLogView,
    MasterAdminOrganisationActionView,
    MasterAdminOrganisationCreationSettingView,
    MasterAdminOrganisationDetailView,
    MasterAdminOrganisationListView,
    MasterAdminStatsView,
    MasterAdminStatusView,
)

urlpatterns = [
    path("status/", MasterAdminStatusView.as_view()),
    path("stats/", MasterAdminStatsView.as_view()),
    path("organisations/", MasterAdminOrganisationListView.as_view()),
    path("organisations/<int:organisation_id>/", MasterAdminOrganisationDetailView.as_view()),
    path("organisations/<int:organisation_id>/<str:action>/", MasterAdminOrganisationActionView.as_view()),
    path("audit-logs/", MasterAdminAuditLogView.as_view()),
    path("settings/organisation-creation/", MasterAdminOrganisationCreationSettingView.as_view()),
]
