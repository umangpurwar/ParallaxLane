"""Core views for ParallaxLane backend."""

from django.http import JsonResponse


def ratelimit_error(request, exception=None):
    """View returned by django-ratelimit middleware when rate limit exceeded."""
    return JsonResponse(
        {"error": "Request rate limit exceeded. Please try again later."},
        status=429,
    )

