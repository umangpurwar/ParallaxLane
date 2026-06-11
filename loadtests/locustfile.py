"""
ParallaxLane load test — 70 concurrent users.

Install: pip install locust
Run:     locust -f loadtests/locustfile.py --host=http://127.0.0.1:8000
Web UI:  http://localhost:8089
Headless: locust -f loadtests/locustfile.py --host=http://127.0.0.1:8000 \
           --users 70 --spawn-rate 10 --run-time 5m --headless
"""

import random
from locust import HttpUser, between, task


class CandidateUser(HttpUser):
    wait_time = between(1, 5)
    token = None
    exam_id = None
    attempt_id = None

    def on_start(self):
        email = f"candidate{random.randint(1, 70)}@loadtest.com"
        res = self.client.post(
            "/api/login/",
            json={"email": email, "password": "TestPass1!"},
            name="/api/login/",
        )
        if res.status_code == 200:
            self.token = res.json().get("access")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(3)
    def heartbeat(self):
        if not self.attempt_id:
            return
        self.client.post(
            "/api/monitoring/heartbeat/",
            json={"attempt_id": self.attempt_id},
            name="/api/monitoring/heartbeat/",
        )

    @task(2)
    def list_exams(self):
        self.client.get("/api/exams/", name="/api/exams/")

    @task(1)
    def health(self):
        self.client.get("/api/health/", name="/api/health/")


class InvigilatorUser(HttpUser):
    wait_time = between(2, 8)
    weight = 1

    def on_start(self):
        res = self.client.post(
            "/api/login/",
            json={"email": "admin@loadtest.com", "password": "TestPass1!"},
            name="/api/login/ [admin]",
        )
        if res.status_code == 200:
            self.client.headers.update({"Authorization": f"Bearer {res.json()['access']}"})

    @task(5)
    def live_monitor(self):
        self.client.get("/api/admin/exam/1/live/", name="/api/admin/exam/live/")

    @task(2)
    def list_exams(self):
        self.client.get("/api/admin/exam/list/", name="/api/admin/exam/list/")
