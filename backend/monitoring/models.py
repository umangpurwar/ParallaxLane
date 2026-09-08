from django.db import models
from exams.models import ExamAttempt


class Violation(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name="violations"
    )

    violation_type = models.CharField(max_length=100)
    severity = models.IntegerField(default=1)

    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["-timestamp"], name="violation_timestamp_desc_idx"),
        ]

    def __str__(self):
        return f"{self.violation_type} - {self.timestamp}"
