import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.ops.serializers import OpsBehaviorQuerySerializer, OpsStorageQuerySerializer
from apps.ops.services import collect_runtime, read_behavior, read_storage
from core.permissions import IsSuperAdmin
from core.responses import error_response, success_response

logger = logging.getLogger("apps.ops")


class OpsRuntimeView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        return success_response(collect_runtime(), request=request)


class OpsStorageView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        serializer = OpsStorageQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(
                "OPS_QUERY_INVALID",
                "参数不正确",
                errors=serializer.errors,
                request=request,
            )
        params = serializer.validated_data
        try:
            payload = read_storage(params["recount"], params["page"], params["page_size"])
        except Exception:
            logger.exception("ops storage scan failed", extra={"recount": params["recount"]})
            return error_response(
                "OPS_STORAGE_SCAN_FAILED",
                "存储统计失败",
                status=500,
                request=request,
            )
        return success_response(payload, request=request)


class OpsBehaviorView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        serializer = OpsBehaviorQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(
                "OPS_QUERY_INVALID",
                "参数不正确",
                errors=serializer.errors,
                request=request,
            )
        return success_response(read_behavior(serializer.validated_data["days"]), request=request)
