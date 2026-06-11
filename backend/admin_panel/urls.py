from django.urls import path
from .views import *

urlpatterns = [
    path("exam/<int:exam_id>/live/", live_monitor),

    path("exam/<int:exam_id>/user/<str:username>/", user_detail_exam),
    path("exam/<int:exam_id>/user/<str:username>/clear/", clear_violations_exam),

    path("user/<str:username>/", user_detail),
    path("user/<str:username>/clear/", clear_violations),

    path("exam/create/", create_exam),
    path("exam/list/", list_exams),
    path("exam/<int:exam_id>/toggle/", toggle_exam),
    path("exam/<int:exam_id>/update/", update_exam),
    path("exam/<int:exam_id>/delete/", delete_exam),
    path("users/", list_all_users),
    path("exam/<int:exam_id>/results/", exam_results),
    path("exam/<int:exam_id>/export/", exam_export_report),
    path("exam/<int:exam_id>/qa/", exam_qa),
]