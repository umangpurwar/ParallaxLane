"""Deployment-wide settings used by the Master Admin boundary."""

from django.conf import settings

from .models import DeploymentSetting


ORGANISATION_CREATION_KEY = "organisation_creation_enabled"


def organisation_creation_enabled():
    override = DeploymentSetting.objects.filter(
        key=ORGANISATION_CREATION_KEY
    ).values_list("boolean_value", flat=True).first()
    if override is None:
        return settings.ORGANISATION_CREATION_ENABLED
    return override


def set_organisation_creation_enabled(enabled, updated_by):
    setting, _ = DeploymentSetting.objects.update_or_create(
        key=ORGANISATION_CREATION_KEY,
        defaults={"boolean_value": enabled, "updated_by": updated_by},
    )
    return setting
