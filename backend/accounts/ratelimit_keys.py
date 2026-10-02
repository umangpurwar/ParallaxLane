"""Shared django-ratelimit key functions."""

from core.ratelimit import email_or_ip


def post_email_key(group, request):
    return email_or_ip(group, request)
