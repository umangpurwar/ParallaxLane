"""Google ID token verification with audience, issuer, and expiry checks."""

import logging

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

logger = logging.getLogger(__name__)

VALID_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


def verify_google_id_token(token):
    """
    Verify a Google ID token and return the decoded claims.
    Raises ValueError on any validation failure.
    """
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None)
    if not client_id:
        raise ValueError("Google OAuth is not configured on the server")

    request = google_requests.Request()
    # Allow small clock drift between Google, client, and server (common on Windows dev machines).
    idinfo = id_token.verify_oauth2_token(
        token,
        request,
        client_id,
        clock_skew_in_seconds=60,
    )

    issuer = idinfo.get("iss")
    if issuer not in VALID_ISSUERS:
        raise ValueError("Invalid token issuer")

    if not idinfo.get("email_verified", False):
        raise ValueError("Google account email is not verified")

    email = idinfo.get("email")
    if not email:
        raise ValueError("Email not found in Google token")

    return idinfo
