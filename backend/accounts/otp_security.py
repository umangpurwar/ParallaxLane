"""OTP verification abuse protection (rate limits + lockout)."""

from django.conf import settings
from django.core.cache import cache


def _key(email, suffix):
    return f"otp:{suffix}:{email.lower().strip()}"


def is_locked_out(email):
    return bool(cache.get(_key(email, "lock")))


def lockout_message():
    minutes = max(1, getattr(settings, "OTP_LOCKOUT_SECONDS", 900) // 60)
    return f"Too many failed attempts. Try again in {minutes} minutes."


def check_verify_allowed(email):
    if not email:
        return False, "Email is required"
    if is_locked_out(email):
        return False, lockout_message()
    return True, None


def record_failed_verify(email):
    if not email:
        return
    fail_key = _key(email, "fails")
    window = getattr(settings, "OTP_VERIFY_WINDOW_SECONDS", 300)
    max_attempts = getattr(settings, "OTP_MAX_VERIFY_ATTEMPTS", 5)
    lockout = getattr(settings, "OTP_LOCKOUT_SECONDS", 900)

    fails = cache.get(fail_key, 0) + 1
    cache.set(fail_key, fails, window)
    if fails >= max_attempts:
        cache.set(_key(email, "lock"), True, lockout)
        cache.delete(fail_key)


def clear_verify_attempts(email):
    if not email:
        return
    cache.delete(_key(email, "fails"))
    cache.delete(_key(email, "lock"))
