from django.db import models


class AttemptEvent(models.Model):
    class EventType(models.TextChoices):
        ATTEMPT_STARTED = "attempt_started", "Attempt started"
        QUESTION_VIEWED = "question_viewed", "Question viewed"
        ANSWER_SAVED = "answer_saved", "Answer saved"
        ANSWER_CHANGED = "answer_changed", "Answer changed"
        QUESTION_SKIPPED = "question_skipped", "Question skipped"
        QUESTION_NAVIGATION = "question_navigation", "Question navigation"
        APP_BACKGROUNDED = "app_backgrounded", "App backgrounded"
        APP_RESUMED = "app_resumed", "App resumed"
        NETWORK_OFFLINE = "network_offline", "Network offline"
        NETWORK_RESTORED = "network_restored", "Network restored"
        EXAM_SUBMITTED = "exam_submitted", "Exam submitted"
        EXAM_TERMINATED = "exam_terminated", "Exam terminated"

    attempt = models.ForeignKey(
        "exams.ExamAttempt",
        on_delete=models.CASCADE,
        related_name="events",
    )
    question = models.ForeignKey(
        "exams.Question",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attempt_events",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["attempt", "timestamp"],
                name="attempt_event_attempt_time_idx",
            ),
            models.Index(
                fields=["event_type", "timestamp"],
                name="attempt_event_type_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} - attempt {self.attempt_id}"
