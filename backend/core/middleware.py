"""Force-upgrade for outdated Android clients."""

from django.conf import settings
from django.http import JsonResponse


class MinimumAppVersionMiddleware:
    """Requests sent with `X-Client: android` must carry X-App-Version >= minimum.

    Web clients send no X-Client header and are unaffected.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path.startswith("/api/")
            and request.headers.get("X-Client", "").lower() == "android"
        ):
            try:
                version = int(request.headers.get("X-App-Version", "0"))
            except ValueError:
                version = 0
            if version < settings.MIN_ANDROID_APP_VERSION:
                return JsonResponse(
                    {
                        "error": "This app version is no longer supported. Please update.",
                        "code": "app_update_required",
                        "min_version": settings.MIN_ANDROID_APP_VERSION,
                    },
                    status=426,
                )
        return self.get_response(request)
