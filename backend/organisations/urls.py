from django.urls import path
from .views import *
from .application_views import ApplicationDetailView, MyApplicationsView, ResubmitApplicationView
from .org_admin_views import (
    DeclineInviteView, MemberActiveView, OrgAuditLogView, OrgInvitesView,
    OrgOverviewView, OrgProfileView, RevokeInviteView,
)
from .device_admin_views import MyPendingInvitesView, OrgDeviceDecisionView, OrgDeviceListView

urlpatterns = [
    path("join/", JoinOrganisationView.as_view()),
    path("join-by-code/", JoinByCodeView.as_view()),
    path("create/", CreateOrganisationView.as_view()),
    path("settings/", OrganisationSettingsView.as_view()),
    path("invites/", MyPendingInvitesView.as_view()),
    path("invites/decline/", DeclineInviteView.as_view()),
    path("applications/mine/", MyApplicationsView.as_view()),
    path("applications/<int:org_id>/", ApplicationDetailView.as_view()),
    path("applications/<int:org_id>/resubmit/", ResubmitApplicationView.as_view()),
    path("<slug:slug>/switch/", SwitchOrganisationView.as_view()),
    path("<slug:slug>/invite/", InviteMemberView.as_view()),
    path("<slug:slug>/members/", OrganisationMembersView.as_view()),
    path("<slug:slug>/members/<int:member_id>/toggle-exam-access/", ToggleMemberExamAccessView.as_view()),
    path("<slug:slug>/join-code/", OrganisationJoinCodeView.as_view()),
    path("<slug:slug>/overview/", OrgOverviewView.as_view()),
    path("<slug:slug>/profile/", OrgProfileView.as_view()),
    path("<slug:slug>/invites/", OrgInvitesView.as_view()),
    path("<slug:slug>/invites/<int:invite_id>/revoke/", RevokeInviteView.as_view()),
    path("<slug:slug>/members/<int:member_id>/<str:action>/", MemberActiveView.as_view()),
    path("<slug:slug>/audit-logs/", OrgAuditLogView.as_view()),
    path("<slug:slug>/devices/", OrgDeviceListView.as_view()),
    path("<slug:slug>/devices/<int:device_pk>/<str:decision>/", OrgDeviceDecisionView.as_view()),
    path("my/", MyOrganisationsView.as_view()),
]
