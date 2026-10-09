"""Writing audit log entries. Kept tiny so every view can call it in one line."""

from .models import AuditLog


def audit(actor, action, organisation=None, target="", **metadata):
    """Record one administrative action. Never raises into the caller's request."""
    AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        organisation=organisation,
        target=str(target)[:255],
        metadata=metadata,
    )


def serialize_log(entry):
    return {
        "id": entry.id,
        "action": entry.action,
        "actor": entry.actor.email if entry.actor_id else None,
        "organisation": (
            {"id": entry.organisation_id, "name": entry.organisation.name}
            if entry.organisation_id else None
        ),
        "target": entry.target,
        "metadata": entry.metadata,
        "created_at": entry.created_at,
    }
