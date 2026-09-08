"""OTP issuance shared by registration and password-recovery flows."""

import secrets

from .models import EmailOTP
from core.email_service import EmailDeliveryError, send_otp_email


def issue_otp(*, email, purpose):
    """Replace any previous OTP, deliver the new one, and return its record."""
    EmailOTP.objects.filter(email=email).delete()
    otp = str(secrets.randbelow(900000) + 100000)
    record = EmailOTP(email=email)
    record.set_otp(otp)
    record.save()
    try:
        send_otp_email(
            recipient=email,
            otp=otp,
            purpose=purpose,
        )
    except EmailDeliveryError:
        record.delete()
        raise
    return record
