from django.conf import settings
from django.db import models


class DeploymentSetting(models.Model):
    """Small persistent store for deployment-wide Master Admin overrides."""

    key = models.CharField(max_length=100, unique=True)
    boolean_value = models.BooleanField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deployment_setting_updates",
    )

    def __str__(self):
        return f"{self.key}={self.boolean_value}"


class AuditLog(models.Model):
    """Append-only record of administrative actions (platform and organisation)."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_actions",
    )
    action = models.CharField(max_length=60, db_index=True)
    organisation = models.ForeignKey(
        "organisations.Organisation", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_logs",
    )
    target = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action}"
