from django.urls import path
from .views import *

urlpatterns = [

    path("log/", LogViolationView.as_view(), name="log_violation"),
    path("heartbeat/", student_heartbeat),

]
