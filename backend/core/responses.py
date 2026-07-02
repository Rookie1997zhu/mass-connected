import uuid

from rest_framework.response import Response


def get_request_id(request):
    return getattr(request, "request_id", None) or ""


def success_response(data=None, message="成功", status=200, request=None):
    return Response(
        {
            "code": "OK",
            "message": message,
            "data": data if data is not None else {},
            "request_id": get_request_id(request) if request else "",
        },
        status=status,
    )


def error_response(code, message, errors=None, status=400, request=None):
    return Response(
        {
            "code": code,
            "message": message,
            "errors": errors or {},
            "request_id": get_request_id(request) if request else "",
        },
        status=status,
    )


def generate_request_id():
    return f"req_{uuid.uuid4().hex[:16]}"
