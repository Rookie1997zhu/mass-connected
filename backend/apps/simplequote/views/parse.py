import os

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.simplequote.calculator import build_param_map, weight_from_volume
from apps.simplequote.heavy_tasks import run_drawing_parse, run_stp_parse
from core.async_jobs import JOB_TTL_SECONDS, create_job, get_job
from core.permissions import IsBuyerRole
from core.responses import error_response, success_response

from apps.simplequote.views._helpers import _save_parse_upload, param_overrides


INJECTION_MATERIALS = ["ABS", "ABS+Gf", "PC", "PA66", "PP"]
MAX_STP_SIZE = 30 * 1024 * 1024  # 30MB
ALLOWED_STP_EXT = (".stp", ".step")
STP_MAGIC = b"ISO-10303-21"


def injection_densities():
    """返回各材料密度映射（后台 QuoteParam 覆盖 DEFAULT_PARAMS 兜底），键为展示材料名。"""
    params = build_param_map("injection", param_overrides("injection"))
    result = {}
    for material in INJECTION_MATERIALS:
        weight = weight_from_volume(1.0, material, params)  # 体积 1cm³ 的重量即密度
        if weight is not None:
            result[material] = weight
    return result


class StpParseView(APIView):
    """上传 STP/STEP 文件，异步解析体积/包围盒/表面积，供注塑报价表单回填。

    POST 立即返回 job_id；结果经 ParseJobDetailView 短轮询取得。
    """

    permission_classes = [IsBuyerRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return error_response(
                "STP_FILE_INVALID", "请上传 STP/STEP 文件", request=request
            )
        name = (upload.name or "").lower()
        if not name.endswith(ALLOWED_STP_EXT):
            return error_response(
                "STP_FILE_INVALID", "仅支持 .stp / .step 文件", request=request
            )
        if upload.size > MAX_STP_SIZE:
            return error_response(
                "STP_FILE_INVALID", "文件超过 30MB 上限，请压缩或改为手动填写", request=request
            )

        head = upload.read(64)
        upload.seek(0)
        if STP_MAGIC not in head:
            return error_response(
                "STP_FILE_INVALID", "文件不是有效的 STEP 格式", request=request
            )

        suffix = ".step" if name.endswith(".step") else ".stp"
        try:
            tmp_path = _save_parse_upload(upload, suffix)
        except OSError:
            return error_response(
                "STP_FILE_INVALID", "文件保存失败，请重试", request=request
            )

        job_id = create_job("stp_parse", request.user.id, meta={"file_name": upload.name})
        run_stp_parse.delay(job_id, tmp_path)
        return success_response(
            {
                "job_id": job_id,
                "status": "pending",
                "expires_in": JOB_TTL_SECONDS,
            },
            message="解析任务已提交",
            status=status.HTTP_202_ACCEPTED,
            request=request,
        )


MAX_DRAWING_SIZE = 15 * 1024 * 1024  # 15MB
ALLOWED_DRAWING_EXT = (".pdf", ".png", ".jpg", ".jpeg")
# 文件魔数：PDF / PNG / JPEG
_DRAWING_MAGICS = (b"%PDF", b"\x89PNG", b"\xff\xd8\xff")


class DrawingParseView(APIView):
    """上传 2D 工程图（PDF/图片），异步 OCR 抽取材料/精密度/颜色作为建议值。

    POST 立即返回 job_id；结果经 ParseJobDetailView 短轮询取得。
    """

    permission_classes = [IsBuyerRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return error_response(
                "DRAWING_FILE_INVALID", "请上传工程图（PDF/PNG/JPG）", request=request
            )
        name = (upload.name or "").lower()
        if not name.endswith(ALLOWED_DRAWING_EXT):
            return error_response(
                "DRAWING_FILE_INVALID", "仅支持 PDF / PNG / JPG 文件", request=request
            )
        if upload.size > MAX_DRAWING_SIZE:
            return error_response(
                "DRAWING_FILE_INVALID", "文件超过 15MB 上限，请压缩或改为手动填写", request=request
            )

        head = upload.read(8)
        upload.seek(0)
        if not any(head.startswith(magic) for magic in _DRAWING_MAGICS):
            return error_response(
                "DRAWING_FILE_INVALID", "文件不是有效的 PDF/图片格式", request=request
            )

        kind = "pdf" if name.endswith(".pdf") else "image"
        suffix = ".pdf" if kind == "pdf" else os.path.splitext(name)[1]
        try:
            tmp_path = _save_parse_upload(upload, suffix)
        except OSError:
            return error_response(
                "DRAWING_FILE_INVALID", "文件保存失败，请重试", request=request
            )

        job_id = create_job(
            "drawing_parse",
            request.user.id,
            meta={"file_name": upload.name, "kind": kind},
        )
        run_drawing_parse.delay(job_id, tmp_path, kind)
        return success_response(
            {
                "job_id": job_id,
                "status": "pending",
                "expires_in": JOB_TTL_SECONDS,
            },
            message="解析任务已提交",
            status=status.HTTP_202_ACCEPTED,
            request=request,
        )


class ParseJobDetailView(APIView):
    """轮询异步解析/预览转换任务状态（仅任务所有者可读）。"""

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = get_job(job_id)
        if not job or job.get("user_id") != request.user.id:
            return error_response(
                "PARSE_JOB_NOT_FOUND",
                "任务不存在或已过期",
                status=status.HTTP_404_NOT_FOUND,
                request=request,
            )

        status_value = job.get("status") or "pending"
        payload = {
            "job_id": job.get("job_id") or job_id,
            "kind": job.get("kind"),
            "status": status_value,
            "result": job.get("result"),
            "error_code": job.get("error_code"),
            "error_message": job.get("error_message"),
            "expires_in": JOB_TTL_SECONDS,
        }
        http_status = status.HTTP_202_ACCEPTED if status_value in {"pending", "running"} else 200
        return success_response(payload, message="OK", status=http_status, request=request)
