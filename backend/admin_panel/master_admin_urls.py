from django.urls import path

from .master_admin_views import (
    MasterAdminOrganisationCreationSettingView,
    MasterAdminOrganisationDetailView,
    MasterAdminOrganisationListView,
    MasterAdminStatusView,
)


urlpatterns = [
    path("status/", MasterAdminStatusView.as_view()),
    path("organisations/", MasterAdminOrganisationListView.as_view()),
    path("organisations/<int:organisation_id>/", MasterAdminOrganisationDetailView.as_view()),
    path(
        "settings/organisation-creation/",
        MasterAdminOrganisationCreationSettingView.as_view(),
    ),
]
