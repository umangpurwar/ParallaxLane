from django.urls import path

from .views import (
    ExamDetailView,
    ExamListView,
    SaveAnswerView,
    StartChallengeView,
    StartExamView,
    SubmitExamView,
    my_results,
)

urlpatterns = [
    path("", ExamListView.as_view()),
    path("my-results/", my_results),
    path("answers/save/", SaveAnswerView.as_view()),
    path("<int:pk>/", ExamDetailView.as_view()),
    path("<int:pk>/challenge/", StartChallengeView.as_view()),
    path("<int:pk>/start/", StartExamView.as_view()),
    path("<int:pk>/submit/", SubmitExamView.as_view()),
]
