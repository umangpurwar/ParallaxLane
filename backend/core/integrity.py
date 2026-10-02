"""Google Play Integrity verdict verification (Standard API, server-side decode).

Verified against Google's documented response format, not against a live
Google project: test with your Play Console internal track before relying on it.
"""

import hashlib
import logging
import time

from django.conf import settings

logger = logging.getLogger(__name__)

_DECODE_URL = "https://playintegrity.googleapis.com/v1/{package}:decodeIntegrityToken"
_SCOPE = "https://www.googleapis.com/auth/playintegrity"
_MAX_TOKEN_AGE_MS = 5 * 60 * 1000
_session = None


class IntegrityUnavailable(Exception):
    """Google could not be reached or the server is misconfigured."""


def request_hash_for(nonce):
    """requestHash the app must pass to StandardIntegrityTokenRequest."""
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


def _get_session():
    global _session
    if _session is None:
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        if not settings.GOOGLE_SERVICE_ACCOUNT_FILE or not settings.PLAY_INTEGRITY_PACKAGE:
            raise IntegrityUnavailable("Play Integrity is not configured")
        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=[_SCOPE]
        )
        _session = AuthorizedSession(credentials)
    return _session


def decode_token(token):
    """Return Google's tokenPayloadExternal dict. Separated for test mocking."""
    try:
        response = _get_session().post(
            _DECODE_URL.format(package=settings.PLAY_INTEGRITY_PACKAGE),
            json={"integrity_token": token},
            timeout=10,
        )
    except IntegrityUnavailable:
        raise
    except Exception as exc:  # network / auth errors
        logger.exception("Play Integrity decode failed")
        raise IntegrityUnavailable(str(exc)) from exc
    if response.status_code != 200:
        logger.warning("Play Integrity decode HTTP %s: %s", response.status_code, response.text[:300])
        if response.status_code >= 500:
            raise IntegrityUnavailable(f"HTTP {response.status_code}")
        return {}
    return response.json().get("tokenPayloadExternal", {})


def evaluate_verdict(payload, expected_request_hash):
    """Return (ok, reason). Pure function over Google's decoded payload."""
    details = payload.get("requestDetails", {})
    if details.get("requestPackageName") != settings.PLAY_INTEGRITY_PACKAGE:
        return False, "package_mismatch"
    if details.get("requestHash") != expected_request_hash:
        return False, "request_hash_mismatch"
    try:
        issued_ms = int(details.get("timestampMillis", 0))
    except (TypeError, ValueError):
        issued_ms = 0
    if abs(time.time() * 1000 - issued_ms) > _MAX_TOKEN_AGE_MS:
        return False, "stale_token"
    if payload.get("appIntegrity", {}).get("appRecognitionVerdict") != "PLAY_RECOGNIZED":
        return False, "app_not_recognized"
    device_verdicts = payload.get("deviceIntegrity", {}).get("deviceRecognitionVerdict") or []
    if "MEETS_DEVICE_INTEGRITY" not in device_verdicts:
        return False, "device_integrity_failed"
    return True, "ok"


def verify_integrity_token(token, nonce):
    """(ok, reason) for a token bound to `nonce`. Raises IntegrityUnavailable."""
    if not token or not isinstance(token, str) or len(token) > 20000:
        return False, "missing_token"
    payload = decode_token(token)
    if not payload:
        return False, "invalid_token"
    return evaluate_verdict(payload, request_hash_for(nonce))
