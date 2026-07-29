"""API views for print3d options, slice jobs, and admin config."""
from __future__ import annotations

import logging
from datetime import timedelta

from django.http import FileResponse
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.simplequote.calculator import calculate
from apps.simplequote.models import Print3dSliceJob, QuoteParam, QuoteTable
from apps.simplequote.print3d_config import (
    PRINT3D_PARAM_DEFAULTS,
    PRINT3D_PARAM_META,
    admin_config_payload,
    build_job_config_snapshot,
    build_print3d_config,
    public_options_payload,
)
from apps.simplequote.print3d_files import validate_print3d_upload
from apps.simplequote.serializers import (
    AdminPrint3dConfigSerializer,
    Print3dSliceJobCreateSerializer,
    Print3dSliceJobSerializer,
)
from core.permissions import IsAdminRole, IsBuyerRole
from core.responses import error_response, success_response

logger = logging.getLogger(__name__)


class Print3dOptionsView(APIView):
    """会员可读的 3D 打印选项（材料/打印机/质量/后处理）。"""

    permission_classes = [IsBuyerRole]

    def get(self, request):
        return success_response(public_options_payload(), request=request)


class Print3dSliceJobListCreateView(APIView):
    permission_classes = [IsBuyerRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        form = {k: request.data.get(k) for k in (
            "material", "quality", "infill_density",
            "support", "quantity", "post_process", "rush",
        )}
        # Normalize multipart string booleans
        for bool_key in ("support", "rush"):
            raw = form.get(bool_key)
            if isinstance(raw, str):
                form[bool_key] = raw.lower() in ("1", "true", "yes", "on")
        serializer = Print3dSliceJobCreateSerializer(data=form)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cfg = build_print3d_config()
        max_bytes = int(cfg.get("max_file_size_mb", 30)) * 1024 * 1024
        err_code, err_msg, ext = validate_print3d_upload(upload, max_bytes)
        if err_code:
            return error_response(err_code, err_msg, request=request)

        try:
            snapshot = build_job_config_snapshot(data)
        except ValueError as exc:
            return error_response("PRINT3D_INPUT_INVALID", str(exc), request=request)

        ttl = getattr(settings, "PRINT3D_SLICE_JOB_TTL_HOURS", 24)
        job = Print3dSliceJob.objects.create(
            buyer=request.user,
            original_filename=(upload.name or "")[:255],
            file_ext=ext,
            status=Print3dSliceJob.STATUS_PENDING,
            inputs=data,
            config_snapshot=snapshot,
            expires_at=timezone.now() + timedelta(hours=ttl),
        )
        job.source_file.save(upload.name, upload, save=True)

        try:
            from apps.simplequote.tasks import run_print3d_slice

            async_result = run_print3d_slice.delay(job.id)
            job.celery_task_id = async_result.id or ""
            job.save(update_fields=["celery_task_id", "updated_at"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("enqueue print3d slice failed job=%s", job.id)
            job.mark_failed("PRINT3D_QUEUE_FAILED", f"无法入队切片任务: {type(exc).__name__}")
            return error_response(
                "PRINT3D_QUEUE_FAILED",
                "切片任务入队失败，请稍后重试",
                request=request,
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return success_response(
            Print3dSliceJobSerializer(job).data,
            message="切片任务已创建",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class Print3dSliceJobDetailView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        job = Print3dSliceJob.objects.filter(pk=pk, buyer=request.user).first()
        if not job:
            return error_response(
                "PRINT3D_JOB_NOT_FOUND",
                "切片任务不存在",
                status=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        return success_response(Print3dSliceJobSerializer(job).data, request=request)


class Print3dSliceJobPreviewView(APIView):
    """鉴权下载切片预览 STL（不经裸 /media）。"""

    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        job = Print3dSliceJob.objects.filter(pk=pk, buyer=request.user).first()
        if not job or not job.preview_file:
            return error_response(
                "PRINT3D_PREVIEW_MISSING",
                "预览文件不存在",
                status=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        name = (job.preview_file.name or "").rsplit("/", 1)[-1] or "preview.stl"
        return FileResponse(job.preview_file.open("rb"), as_attachment=False, filename=name)


class AdminPrint3dConfigView(APIView):
    """管理员读写完整 print3d 配置（参数 + 表格）。"""

    permission_classes = [IsAdminRole]

    def get(self, request):
        return success_response(admin_config_payload(), request=request)

    def put(self, request):
        serializer = AdminPrint3dConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "params" in data and isinstance(data["params"], dict):
            for key, value in data["params"].items():
                if key not in PRINT3D_PARAM_DEFAULTS:
                    continue
                label, unit = PRINT3D_PARAM_META.get(key, (key, ""))
                QuoteParam.objects.update_or_create(
                    quote_type="print3d",
                    param_key=key,
                    defaults={
                        "value": value,
                        "label": label,
                        "unit": unit,
                        "is_active": True,
                    },
                )

        table_map = {
            "materials": "materials",
            "printers": "printers",
            "qualities": "print_qualities",
            "post_processing": "post_processing",
        }
        for payload_key, table_key in table_map.items():
            if payload_key in data and isinstance(data[payload_key], list):
                QuoteTable.objects.update_or_create(
                    quote_type="print3d",
                    table_key=table_key,
                    defaults={"rows": data[payload_key], "is_active": True},
                )

        return success_response(admin_config_payload(), message="已保存", request=request)


class AdminPrint3dPreviewView(APIView):
    """管理员用样例重量/时长试算费用明细（不扣点）。"""

    permission_classes = [IsAdminRole]

    def post(self, request):
        data = request.data or {}
        try:
            snapshot = build_job_config_snapshot(
                {
                    "material": data.get("material", "PLA"),
                    "printer": data.get("printer", "prusa_mk3s"),
                    "quality": data.get("quality", "standard"),
                    "infill_density": data.get("infill_density", 20),
                    "support": data.get("support", False),
                    "quantity": data.get("quantity", 1),
                    "post_process": data.get("post_process", "none"),
                    "rush": data.get("rush", False),
                }
            )
        except ValueError as exc:
            return error_response("PRINT3D_INPUT_INVALID", str(exc), request=request)

        inputs = {
            "material": snapshot["material"]["key"],
            "printer": snapshot["printer"]["key"],
            "quality": snapshot["quality"]["key"],
            "post_process": snapshot["post_processing"]["key"],
            "model_weight_g": data.get("model_weight_g", 30),
            "print_hours": data.get("print_hours", 4),
            "quantity": snapshot["quantity"],
            "rush": snapshot["rush"],
            "config_snapshot": snapshot,
        }
        result = calculate("print3d", inputs, snapshot.get("params") or {})
        return success_response(result, message="试算完成", request=request)
