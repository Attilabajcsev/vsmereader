import uuid
from django.utils.deprecation import MiddlewareMixin
from core import settings as core_settings


class RequestIdMiddleware(MiddlewareMixin):
    def process_request(self, request):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        core_settings._request_id_ctx.request_id = rid
        request.request_id = rid

    def process_response(self, request, response):
        rid = getattr(request, "request_id", getattr(core_settings, "_request_id_ctx", None).request_id if hasattr(core_settings, "_request_id_ctx") else None)
        if rid:
            response["X-Request-ID"] = rid
        return response


