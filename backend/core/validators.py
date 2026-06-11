"""Shared input validation helpers."""

from django.core.exceptions import ValidationError
from django.core.validators import validate_email


def normalize_email(value):
    """Return lowercased stripped email or raise ValueError."""
    if not value or not isinstance(value, str):
        raise ValueError("Email is required")
    email = value.lower().strip()
    if not email:
        raise ValueError("Email is required")
    try:
        validate_email(email)
    except ValidationError:
        raise ValueError("Invalid email format") from None
    return email


def parse_positive_int(value, field_name="value"):
    """Parse a positive integer from request data."""
    if value is None or value == "":
        raise ValueError(f"{field_name} is required")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {field_name}") from None
    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return parsed


def parse_attempt_id(value):
    """Parse attempt_id; rejects non-numeric values before ORM lookup."""
    if value is None or value == "":
        raise ValueError("attempt_id is required")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("Invalid attempt_id") from None
    if parsed <= 0:
        raise ValueError("Invalid attempt_id")
    return parsed


def validate_org_name(value):
    """Validate organisation name length."""
    if not value or not isinstance(value, str):
        raise ValueError("Organisation name is required")
    name = value.strip()
    if not name:
        raise ValueError("Organisation name is required")
    if len(name) > 200:
        raise ValueError("Organisation name must be 200 characters or fewer")
    return name
