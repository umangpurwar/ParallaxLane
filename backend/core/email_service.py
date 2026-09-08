"""Provider-agnostic transactional email delivery."""

from dataclasses import dataclass

import requests
from django.conf import settings
from django.core.mail import send_mail


class EmailDeliveryError(Exception):
    """Raised when the configured email provider cannot deliver a message."""


@dataclass(frozen=True)
class EmailMessage:
    subject: str
    text: str
    recipient: str


def _configured_message(message):
    return {
        "sender": {
            "email": settings.DEFAULT_FROM_EMAIL,
            "name": settings.EMAIL_FROM_NAME,
        },
        "to": [{"email": message.recipient}],
        "subject": message.subject,
        "textContent": message.text,
    }


def send_email(*, subject, text, recipient):
    """Send one message using the configured console or Brevo provider."""
    message = EmailMessage(subject, text, recipient)
    provider = settings.EMAIL_PROVIDER

    if provider == "console":
        try:
            send_mail(
                message.subject,
                message.text,
                settings.DEFAULT_FROM_EMAIL,
                [message.recipient],
                fail_silently=False,
            )
        except Exception as exc:
            raise EmailDeliveryError("Email delivery failed") from exc
        return

    if provider == "brevo":
        if not settings.BREVO_API_KEY:
            raise EmailDeliveryError("Brevo email delivery is not configured")
        try:
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "accept": "application/json",
                    "api-key": settings.BREVO_API_KEY,
                    "content-type": "application/json",
                },
                json=_configured_message(message),
                timeout=settings.EMAIL_PROVIDER_TIMEOUT,
            )
            response.raise_for_status()
        except Exception as exc:
            raise EmailDeliveryError("Email delivery failed") from exc
        return

    raise EmailDeliveryError("Email provider is not configured correctly")


def send_otp_email(*, recipient, otp, purpose):
    if purpose == "password_reset":
        subject = "Your ParallaxLane password reset code"
        heading = "Reset your password"
        code_label = "Your password reset code is:"
        closing = "If you did not request a password reset, you can ignore this email."
    else:
        subject = "Your ParallaxLane verification code"
        heading = "Verify your email"
        code_label = "Your verification code is:"
        closing = "If you did not create a ParallaxLane account, you can ignore this email."
    send_email(
        subject=subject,
        recipient=recipient,
        text=(
            f"ParallaxLane\n\n{heading}\n\n{code_label}\n\n{otp}\n\n"
            f"This code expires in 5 minutes.\n\n{closing}"
        ),
    )


def send_invitation_email(*, recipient, organisation_name, role, invitation_code, expires_at):
    expiry = expires_at.isoformat() if expires_at else "the configured invitation period"
    send_email(
        subject=f"Invitation to join {organisation_name} on ParallaxLane",
        recipient=recipient,
        text=(
            f"You have been invited to join {organisation_name} on ParallaxLane.\n"
            f"Role: {role}\n"
            f"Invitation code: {invitation_code}\n"
            f"Expires: {expiry}\n\n"
            "Use this invitation code in ParallaxLane to accept the invitation."
        ),
    )
