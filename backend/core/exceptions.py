"""API error handling shared by all DRF views."""

from django_ratelimit.exceptions import Ratelimited
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    # django-ratelimit raises a PermissionDenied subclass; without this DRF
    # turns it into a 403 that clients mistake for "exam terminated".
    if isinstance(exc, Ratelimited):
        return Response(
            {"error": "Too many requests. Try again shortly.", "code": "rate_limited"},
            status=429,
            headers={"Retry-After": "60"},
        )
    return exception_handler(exc, context)


def api_error(code, message, status, **extra):
    """Error body with a stable machine-readable code for app clients."""
    body = {"error": message, "code": code}
    body.update(extra)
    return Response(body, status=status)
