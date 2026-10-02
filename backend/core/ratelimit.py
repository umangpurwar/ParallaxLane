"""Client IP resolution for django-ratelimit.

Set TRUST_PROXY_IP_HEADER=True only when Django is reachable exclusively
through a reverse proxy that sets X-Real-IP (otherwise clients could spoof it
to dodge per-IP limits).
"""

from django.conf import settings


def client_ip(request):
    if getattr(settings, "TRUST_PROXY_IP_HEADER", False):
        forwarded = request.META.get("HTTP_X_REAL_IP")
        if forwarded:
            return forwarded.strip()
    return request.META.get("REMOTE_ADDR") or "unknown"


def email_or_ip(group, request):
    """Key for unauthenticated endpoints: per email, falling back to IP."""
    email = ""
    data = getattr(request, "data", None)
    if data is None and request.method == "POST":
        data = request.POST
    try:
        email = (data.get("email") or "").lower().strip() if data else ""
    except AttributeError:
        email = ""
    return email or client_ip(request)
