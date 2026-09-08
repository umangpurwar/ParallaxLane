import logging

from django.db import transaction

from .models import AttemptEvent


logger = logging.getLogger(__name__)


def record_attempt_event(attempt, event_type, question=None, metadata=None):
    """Best-effort append-only event recording isolated from exam operations."""
    try:
        with transaction.atomic():
            event = AttemptEvent.objects.create(
                attempt=attempt,
                question=question,
                event_type=event_type,
                metadata=metadata or {},
            )
    except Exception:
        logger.exception(
            "Unable to record attempt event %s for attempt %s",
            event_type,
            getattr(attempt, "id", None),
        )
        return None

    return event
