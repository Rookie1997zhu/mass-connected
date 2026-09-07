import logging

from rest_framework import status
from rest_framework.exceptions import APIException, Throttled, ValidationError
from rest_framework.views import exception_handler

from core.responses import error_response

logger = logging.getLogger(__name__)

HTTP_STATUS_TO_CODE = {
    status.HTTP_401_UNAUTHORIZED: "AUTH_TOKEN_INVALID",
    status.HTTP_403_FORBIDDEN: "AUTH_PERMISSION_DENIED",
    status.HTTP_404_NOT_FOUND: "COMMON_NOT_FOUND",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMIT_EXCEEDED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "COMMON_INTERNAL_ERROR",
}


class AppAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "COMMON_VALIDATION_ERROR"
    default_detail = "请求失败"

    def __init__(self, detail=None, code=None, errors=None):
        self.errors = errors or {}
        # Instance attr so custom_exception_handler can read the real code
        # (class default_code would otherwise always shadow the constructor arg).
        resolved = code or self.default_code
        self.default_code = resolved
        super().__init__(detail=detail, code=resolved)


def custom_exception_handler(exc, context):
    request = context.get("request")
    response = exception_handler(exc, context)

    if response is not None:
        code = getattr(exc, "default_code", None) or HTTP_STATUS_TO_CODE.get(
            response.status_code, "COMMON_VALIDATION_ERROR"
        )
        if isinstance(exc, Throttled):
            code = "RATE_LIMIT_EXCEEDED"
        elif isinstance(exc, ValidationError):
            code = "COMMON_VALIDATION_ERROR"
        errors = getattr(exc, "errors", None)
        detail = getattr(exc, "detail", None)
        if errors is None and isinstance(detail, dict):
            errors = detail
        elif errors is None and detail is not None:
            errors = {"detail": detail}

        if response.status_code >= 500:
            logger.exception("Unhandled API error", extra={"request_id": getattr(request, "request_id", "")})

        return error_response(
            code=code,
            message=str(detail) if detail is not None else "请求失败",
            errors=errors if isinstance(errors, dict) else {},
            status=response.status_code,
            request=request,
        )

    logger.exception("Unhandled exception", extra={"request_id": getattr(request, "request_id", "")})
    return error_response(
        code="COMMON_INTERNAL_ERROR",
        message="服务器内部错误",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request=request,
    )
