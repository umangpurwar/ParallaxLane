from django.urls import path
from .views import *

urlpatterns = [
    path("join/", JoinOrganisationView.as_view()),
    path("join-by-code/", JoinByCodeView.as_view()),
    path("create/", CreateOrganisationView.as_view()),
    path("settings/", OrganisationSettingsView.as_view()),
    path("<slug:slug>/switch/", SwitchOrganisationView.as_view()),
    path("<slug:slug>/invite/", InviteMemberView.as_view()),
    path("<slug:slug>/members/", OrganisationMembersView.as_view()),
    path("<slug:slug>/members/<int:member_id>/toggle-exam-access/", ToggleMemberExamAccessView.as_view()),
    path("<slug:slug>/join-code/", OrganisationJoinCodeView.as_view()),
    path("my/", MyOrganisationsView.as_view()),
]
