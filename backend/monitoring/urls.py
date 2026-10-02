from django.urls import path

from .views import AttemptEventsView, HeartbeatView, LogViolationView

urlpatterns = [
    path("log/", LogViolationView.as_view(), name="log_violation"),
    path("heartbeat/", HeartbeatView.as_view(), name="heartbeat"),
    path("events/", AttemptEventsView.as_view(), name="attempt_events"),
]
