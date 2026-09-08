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
