"""Candidate device registration (trust-on-first-use, admin approval for changes)."""

from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.devices import load_public_key, normalize_device_id
from core.exceptions import api_error
from exams.models import ExamAttempt

from .models import UserDevice


def serialize_device(device):
    return {
        "id": device.id,
        "device_id": device.device_id,
        "model_name": device.model_name,
        "status": device.status,
        "pending_reason": device.pending_reason,
        "created_at": device.created_at,
        "approved_at": device.approved_at,
        "last_seen": device.last_seen,
    }


class RegisterDeviceView(APIView):
    """Register (or re-key) this phone for exams.

    - First device of an account is approved automatically.
    - Same device re-installing the app (same device_id, new Keystore key) is
      re-keyed automatically.
    - A different device, or a device already approved for another account,
      stays pending until an org admin approves it.
    - Nothing changes while the user has an active exam attempt.
    """

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="user", rate="5/m", method="POST", block=True))
    def post(self, request):
        device_id = normalize_device_id(request.data.get("device_id"))
        if not device_id:
            return api_error("invalid_device_id", "device_id must be a 64-char SHA-256 hex", 400)
        public_key = request.data.get("public_key")
        try:
            load_public_key(public_key)
        except ValueError as exc:
            return api_error("invalid_public_key", str(exc), 400)
        model_name = str(request.data.get("model_name") or "")[:100]
        user = request.user

        if ExamAttempt.objects.filter(user=user, status="active").exists():
            return api_error(
                "device_change_during_exam", "Devices can't change during an active exam", 409
            )

        try:
            with transaction.atomic():
                device = self._register(user, device_id, public_key, model_name)
        except IntegrityError:
            return api_error("conflict", "Concurrent registration, retry", 409)
        return Response(serialize_device(device))

    @staticmethod
    def _register(user, device_id, public_key, model_name):
        live = UserDevice.objects.select_for_update().filter(user=user).exclude(
            status=UserDevice.STATUS_REVOKED
        )
        same = live.filter(device_id=device_id).first()
        approved = live.filter(status=UserDevice.STATUS_APPROVED).first()

        if same:
            # Re-install on the same phone: accept the new Keystore key.
            same.public_key = public_key
            same.model_name = model_name or same.model_name
            same.save(update_fields=["public_key", "model_name"])
            return same

        shared = UserDevice.objects.filter(
            device_id=device_id, status=UserDevice.STATUS_APPROVED
        ).exclude(user=user).exists()

        if approved is None and not shared:
            return UserDevice.objects.create(
                user=user,
                device_id=device_id,
                public_key=public_key,
                model_name=model_name,
                status=UserDevice.STATUS_APPROVED,
                approved_at=now(),
            )

        # A second pending request replaces the previous pending one.
        live.filter(status=UserDevice.STATUS_PENDING).update(status=UserDevice.STATUS_REVOKED)
        return UserDevice.objects.create(
            user=user,
            device_id=device_id,
            public_key=public_key,
            model_name=model_name,
            status=UserDevice.STATUS_PENDING,
            pending_reason="shared_device" if shared else "device_change",
        )


class MyDevicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        devices = UserDevice.objects.filter(user=request.user).exclude(
            status=UserDevice.STATUS_REVOKED
        ).order_by("-created_at")
        return Response([serialize_device(device) for device in devices])
