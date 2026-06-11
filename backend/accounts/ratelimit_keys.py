"""Shared django-ratelimit key functions."""


def post_email_key(group, request):
    email = ""
    if hasattr(request, "data") and request.data:
        email = (request.data.get("email") or "").lower().strip()
    return email or request.META.get("REMOTE_ADDR", "unknown")
