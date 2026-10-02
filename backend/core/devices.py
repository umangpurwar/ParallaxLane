"""Exam device binding: device lookup, key handling and the DRF permission."""

import base64
import binascii
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.utils.timezone import now
from rest_framework.permissions import BasePermission

from accounts.models import UserDevice

DEVICE_HEADER = "X-Device-Id"
_DEVICE_ID_RE = re.compile(r"^[0-9a-f]{64}$")


def normalize_device_id(value):
    """Return the lowercase 64-hex device id, or None if malformed."""
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    return value if _DEVICE_ID_RE.match(value) else None


def load_public_key(b64_value):
    """Parse a base64 SubjectPublicKeyInfo EC P-256 key; raise ValueError if invalid."""
    if not isinstance(b64_value, str) or len(b64_value) > 1024:
        raise ValueError("public_key must be a base64 string")
    try:
        der = base64.b64decode(b64_value, validate=True)
        key = serialization.load_der_public_key(der)
    except (binascii.Error, ValueError, TypeError):
        raise ValueError("public_key is not a valid base64 DER public key") from None
    if not isinstance(key, ec.EllipticCurvePublicKey) or key.curve.name != "secp256r1":
        raise ValueError("public_key must be an EC P-256 key")
    return key


def verify_signature(device, message, signature_b64):
    """Verify a SHA256withECDSA (DER) signature made by the device's Keystore key."""
    try:
        signature = base64.b64decode(signature_b64 or "", validate=True)
        load_public_key(device.public_key).verify(
            signature, message.encode("utf-8"), ec.ECDSA(hashes.SHA256())
        )
        return True
    except (InvalidSignature, binascii.Error, ValueError, TypeError):
        return False


def approved_device_for(request):
    """The user's approved device matching the X-Device-Id header, or None."""
    device_id = normalize_device_id(request.headers.get(DEVICE_HEADER))
    if not device_id or not request.user or not request.user.is_authenticated:
        return None
    return UserDevice.objects.filter(
        user=request.user, device_id=device_id, status=UserDevice.STATUS_APPROVED
    ).first()


class HasApprovedDevice(BasePermission):
    """Candidate exam endpoints only answer requests from the user's approved device."""

    message = {
        "error": "This device is not approved for exams. Register it in the app.",
        "code": "device_not_approved",
    }

    def has_permission(self, request, view):
        if not settings.DEVICE_REQUIRED_FOR_EXAMS:
            request.exam_device = None
            return True
        device = approved_device_for(request)
        if device is None:
            return False
        request.exam_device = device
        UserDevice.objects.filter(pk=device.pk).update(last_seen=now())
        return True
