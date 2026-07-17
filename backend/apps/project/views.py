from django.shortcuts import get_object_or_404
from django.utils import timezone
from pathlib import Path
import logging
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from apps.notification.services import notify
from apps.project.models import (
    Project,
    ProjectFile,
    ProjectIssue,
    ProjectStage,
    ProjectTodo,
    ProjectUpdate,
)
from apps.project.serializers import (
    ProjectDetailSerializer,
    ProjectFileSerializer,
    ProjectIssueSerializer,
    ProjectListSerializer,
    ProjectStageSerializer,
    ProjectTodoAggregateSerializer,
    ProjectTodoSerializer,
    ProjectUpdateSerializer,
)
from apps.project.services import get_current_stage, recalc_progress
from apps.project.translation import (
    TranslationError,
    translate_project_file_text,
    translate_project_pdf_file,
    translate_text,
)
from core.document_preview import (
    PDF_EXT,
    PreviewError,
    cleanup_preview_cache,
    extract_text_from_file,
    file_ext,
    get_or_create_preview_pdf,
    preview_mode_for_ext,
)
from core.file_validation import validate_upload_file
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response

logger = logging.getLogger(__name__)


def _project_translate_response(request, _project):
    text = request.data.get("text", "")
    target_lang = request.data.get("target_lang", "")
    try:
        translated = translate_text(text, target_lang)
    except TranslationError as exc:
        status_code = 503 if exc.code == "TRANSLATE_NOT_CONFIGURED" else 400
        if exc.code == "TRANSLATE_FAILED":
            status_code = 502
        return error_response(exc.code, exc.message, status=status_code, request=request)
    return success_response({"translated_text": translated}, request=request)


class IsAuthenticatedPlatformUser(BasePermission):
    message = "需要登录"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        return user.role in {"super_admin", "operator", "sales", "member", "factory"}


class MemberProjectListView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Project.objects.filter(buyer=request.user).select_related(
            "supplier", "rfq", "production_order", "production_order__quote"
        ).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ProjectListSerializer(page, many=True).data)


class MemberProjectDetailView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        project = get_object_or_404(
            Project.objects.select_related(
                "rfq", "production_order", "production_order__quote", "supplier"
            ).prefetch_related(
                "stages", "updates", "todos", "issues", "files__stage", "files__uploader"
            ),
            pk=pk,
            buyer=request.user,
        )
        return success_response(
            ProjectDetailSerializer(
                project, context={"customer_only": True, "request": request}
            ).data,
            request=request,
        )


class MemberProjectTranslateView(APIView):
    permission_classes = [IsBuyerRole]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, buyer=request.user)
        return _project_translate_response(request, project)


class MemberProjectTodoToggleView(APIView):
    permission_classes = [IsBuyerRole]

    def post(self, request, pk, todo_id):
        project = get_object_or_404(Project, pk=pk, buyer=request.user)
        todo = get_object_or_404(ProjectTodo, pk=todo_id, project=project, assignee_type="customer")
        todo.is_done = not todo.is_done
        todo.save(update_fields=["is_done"])
        return success_response(ProjectTodoSerializer(todo).data, request=request)


class SupplierProjectListView(APIView):
    permission_classes = [IsSupplierRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Project.objects.filter(supplier=request.user).select_related(
            "rfq", "production_order", "production_order__quote"
        ).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ProjectListSerializer(page, many=True).data)


class SupplierProjectDetailView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk):
        project = get_object_or_404(
            Project.objects.select_related(
                "rfq", "production_order", "production_order__quote", "supplier"
            ).prefetch_related(
                "stages", "updates", "todos", "issues", "files__stage", "files__uploader"
            ),
            pk=pk,
            supplier=request.user,
        )
        return success_response(
            ProjectDetailSerializer(project, context={"request": request}).data,
            request=request,
        )


class SupplierProjectTranslateView(APIView):
    permission_classes = [IsSupplierRole]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        return _project_translate_response(request, project)


class SupplierProjectUpdateCreateView(APIView):
    permission_classes = [IsSupplierRole]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        content = request.data.get("content", "").strip()
        if not content:
            return error_response("PROJECT_UPDATE_CONTENT_REQUIRED", "进度内容不能为空", request=request)
        stage_id = request.data.get("stage") or request.data.get("stage_id") or None
        stage = None
        if stage_id:
            stage = ProjectStage.objects.filter(pk=stage_id, project=project).first()
            if not stage:
                return error_response(
                    "PROJECT_STAGE_NOT_FOUND",
                    "阶段不存在或不属于该项目",
                    request=request,
                )
        else:
            stage = get_current_stage(project)
        update = ProjectUpdate.objects.create(
            project=project,
            stage=stage,
            author=request.user,
            content=content,
            is_customer_visible=bool(request.data.get("is_customer_visible", True)),
        )
        if update.is_customer_visible:
            notify(
                project.buyer,
                "project",
                "项目进度更新",
                f"项目 {project.project_no} 有新的进度更新。",
                related_type="project",
                related_id=project.id,
                send_email=True,
            )
        return success_response(
            ProjectUpdateSerializer(update).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class SupplierProjectStageUpdateView(APIView):
    permission_classes = [IsSupplierRole]

    def patch(self, request, pk, stage_id):
        from apps.project.services import advance_next_stage

        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        stage = get_object_or_404(ProjectStage, pk=stage_id, project=project)
        new_status = request.data.get("status")
        if new_status not in {"pending", "in_progress", "completed"}:
            return error_response("PROJECT_STAGE_STATUS_INVALID", "无效的阶段状态", request=request)

        stages = list(project.stages.order_by("sort_order", "id"))
        if new_status == "in_progress":
            # 仅允许把当前可推进阶段设为进行中
            current = next((s for s in stages if s.status == "in_progress"), None)
            if current and current.id != stage.id:
                return error_response(
                    "PROJECT_STAGE_ORDER_INVALID",
                    "请先完成当前进行中的阶段",
                    request=request,
                )
            prev_incomplete = [
                s for s in stages if s.sort_order < stage.sort_order and s.status != "completed"
            ]
            if prev_incomplete:
                return error_response(
                    "PROJECT_STAGE_ORDER_INVALID",
                    "请按顺序推进制作流程",
                    request=request,
                )
        if new_status == "completed":
            prev_incomplete = [
                s for s in stages if s.sort_order < stage.sort_order and s.status != "completed"
            ]
            if prev_incomplete:
                return error_response(
                    "PROJECT_STAGE_ORDER_INVALID",
                    "请按顺序完成制作流程",
                    request=request,
                )

        stage.status = new_status
        if new_status == "in_progress" and not stage.started_at:
            stage.started_at = timezone.now()
        if new_status == "completed" and not stage.completed_at:
            stage.completed_at = timezone.now()
        stage.save(update_fields=["status", "started_at", "completed_at"])
        if new_status == "completed":
            advance_next_stage(project, stage)
        recalc_progress(project)
        return success_response(ProjectStageSerializer(stage).data, request=request)


class SupplierProjectIssueCreateView(APIView):
    permission_classes = [IsSupplierRole]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        serializer = ProjectIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issue = serializer.save(project=project, created_by=request.user)
        notify(
            project.buyer,
            "project",
            "项目异常反馈",
            f"项目 {project.project_no} 上报问题：{issue.title}",
            related_type="project",
            related_id=project.id,
        )
        return success_response(
            ProjectIssueSerializer(issue).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminProjectListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Project.objects.select_related("supplier", "buyer").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ProjectListSerializer(page, many=True).data)


class AdminProjectDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        project = get_object_or_404(
            Project.objects.prefetch_related(
                "stages", "updates", "todos", "issues", "files__stage", "files__uploader"
            ),
            pk=pk,
        )
        return success_response(
            ProjectDetailSerializer(project, context={"request": request}).data,
            request=request,
        )

    def patch(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        new_status = request.data.get("status")
        if new_status and new_status not in {c[0] for c in Project.STATUS_CHOICES}:
            return error_response("PROJECT_STATUS_INVALID", "无效的项目状态", request=request)
        if new_status:
            project.status = new_status
        if "progress_percent" in request.data:
            try:
                project.progress_percent = max(0, min(100, int(request.data["progress_percent"])))
            except (TypeError, ValueError):
                return error_response("PROJECT_PROGRESS_INVALID", "无效的进度值", request=request)
        if "expected_delivery_date" in request.data:
            project.expected_delivery_date = request.data.get("expected_delivery_date") or None
        update_fields = ["status", "expected_delivery_date", "updated_at"]
        if "progress_percent" in request.data:
            update_fields.append("progress_percent")
        project.save(update_fields=update_fields)
        return success_response(ProjectDetailSerializer(project).data, request=request)


class AdminProjectTodoCreateView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        serializer = ProjectTodoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        todo = serializer.save(project=project)
        if todo.assignee_type == "customer":
            notify(project.buyer, "project", "有新的待办事项", f"项目 {project.project_no}：{todo.title}",
                   related_type="project", related_id=project.id)
        return success_response(
            ProjectTodoSerializer(todo).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminProjectStageCreateView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        serializer = ProjectStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stage = serializer.save(project=project)
        recalc_progress(project)
        return success_response(
            ProjectStageSerializer(stage).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class MemberTodoAggregateView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request):
        qs = (
            ProjectTodo.objects.filter(project__buyer=request.user, assignee_type="customer")
            .select_related("project")
            .order_by("is_done", "due_date", "id")
        )
        return success_response(
            {"items": ProjectTodoAggregateSerializer(qs, many=True).data},
            request=request,
        )


class MemberFileCenterView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request):
        from apps.rfq.models import RFQAttachment

        project_files = (
            ProjectFile.objects.filter(project__buyer=request.user, visibility="all")
            .select_related("project", "uploader")
            .order_by("-created_at")
        )
        rfq_files = (
            RFQAttachment.objects.filter(rfq__buyer=request.user)
            .select_related("rfq")
            .order_by("-uploaded_at")
        )
        items = []
        for pf in project_files:
            data = ProjectFileSerializer(pf, context={"request": request}).data
            data["source"] = "project"
            data["source_no"] = pf.project.project_no
            items.append(data)
        for af in rfq_files:
            url = request.build_absolute_uri(af.file.url) if af.file else ""
            items.append(
                {
                    "id": af.id,
                    "file_name": af.file_name,
                    "file_category": "rfq",
                    "visibility": "all",
                    "file_url": url,
                    "uploader_name": "—",
                    "created_at": af.uploaded_at.isoformat(),
                    "source": "rfq",
                    "source_no": af.rfq.rfq_no,
                }
            )
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return success_response({"items": items}, request=request)


def _create_project_file(request, project, default_visibility="all", *, fallback_current_stage=False):
    file_obj = request.FILES.get("file")
    code, msg = validate_upload_file(file_obj)
    if code:
        return None, error_response(code, msg, request=request)

    allowed_categories = {c[0] for c in ProjectFile.CATEGORY_CHOICES}
    file_category = request.data.get("file_category", "other")
    if file_category not in allowed_categories:
        return None, error_response(
            "PROJECT_FILE_CATEGORY_INVALID",
            "无效的文件分类",
            errors={"file_category": list(allowed_categories)},
            request=request,
        )

    stage = None
    stage_id = request.data.get("stage") or request.data.get("stage_id")
    if stage_id:
        stage = ProjectStage.objects.filter(pk=stage_id, project=project).first()
        if not stage:
            return None, error_response(
                "PROJECT_STAGE_NOT_FOUND",
                "阶段不存在或不属于该项目",
                request=request,
            )
    elif fallback_current_stage:
        stage = get_current_stage(project)
        if not stage:
            return None, error_response(
                "PROJECT_STAGE_REQUIRED",
                "当前无进行中的阶段，无法上传文件",
                request=request,
            )

    visibility = request.data.get("visibility", default_visibility)
    if visibility not in {"all", "internal"}:
        visibility = default_visibility

    pf = ProjectFile.objects.create(
        project=project,
        stage=stage,
        uploader=request.user,
        file=file_obj,
        file_name=file_obj.name,
        file_category=file_category,
        visibility=visibility,
    )
    return pf, None


def _user_can_access_project_file(user, project, pf):
    role = getattr(user, "role", "")
    if role == "admin":
        return True
    if project.buyer_id == user.id:
        return pf.visibility == "all"
    if project.supplier_id == user.id:
        return True
    return False


def _preview_error_response(exc: PreviewError, request):
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.code == "PREVIEW_PDF_NOT_APPLICABLE":
        status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    elif exc.code in {"PREVIEW_CONVERT_TIMEOUT", "PREVIEW_CONVERT_FAILED"}:
        status_code = status.HTTP_502_BAD_GATEWAY
    elif exc.code == "PREVIEW_CONVERT_UNAVAILABLE":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return error_response(exc.code, exc.message, status=status_code, request=request)


def _preview_project_file_pdf(request, project, file_id):
    from django.http import FileResponse

    pf = get_object_or_404(ProjectFile, pk=file_id, project=project)
    if not _user_can_access_project_file(request.user, project, pf):
        return error_response(
            "PROJECT_FILE_FORBIDDEN",
            "无权访问该文件",
            status=status.HTTP_403_FORBIDDEN,
            request=request,
        )
    if not pf.file:
        return error_response("PROJECT_FILE_MISSING", "文件不存在", request=request)

    ext = file_ext(pf.file_name or pf.file.name)
    mode = preview_mode_for_ext(ext)
    if mode not in {"direct", "pdf_convert"}:
        return error_response(
            "PREVIEW_PDF_NOT_APPLICABLE",
            "该文件类型不支持 PDF 预览",
            status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            request=request,
        )

    try:
        source_path = pf.file.path
        pdf_path = get_or_create_preview_pdf(source_path, pf.id, ext)
    except PreviewError as exc:
        return _preview_error_response(exc, request)
    except Exception:
        logger.exception("preview pdf failed file_id=%s", pf.id)
        return error_response(
            "PREVIEW_CONVERT_FAILED",
            "文档转换失败，请下载原件查看",
            status=status.HTTP_502_BAD_GATEWAY,
            request=request,
        )

    response = FileResponse(
        pdf_path.open("rb"),
        content_type="application/pdf",
        as_attachment=False,
        filename=f"{Path(pf.file_name or 'preview').stem}.pdf",
    )
    response["Content-Disposition"] = 'inline; filename="preview.pdf"'
    return response


def _translate_project_file_response(request, project, file_id):
    pf = get_object_or_404(ProjectFile, pk=file_id, project=project)
    if not _user_can_access_project_file(request.user, project, pf):
        return error_response(
            "PROJECT_FILE_FORBIDDEN",
            "无权访问该文件",
            status=status.HTTP_403_FORBIDDEN,
            request=request,
        )
    if not pf.file:
        return error_response("PROJECT_FILE_MISSING", "文件不存在", request=request)

    target_lang = request.data.get("target_lang", "")
    ext = file_ext(pf.file_name or pf.file.name)

    try:
        if ext == PDF_EXT:
            result = translate_project_pdf_file(pf.id, pf.file.path, target_lang)
        else:
            extracted = extract_text_from_file(pf.file.path, ext)
            translated = translate_project_file_text(pf.id, extracted["text"], target_lang)
            result = {
                "translated_text": translated,
                "source_text": extracted.get("text", ""),
                "truncated": extracted.get("truncated", False),
                "extraction_method": extracted.get("extraction_method", ""),
                "page_count": extracted.get("page_count", 0),
                "processed_pages": extracted.get("page_count", 0),
                "char_count": extracted.get("char_count", 0),
            }
    except PreviewError as exc:
        return error_response(exc.code, exc.message, status=status.HTTP_400_BAD_REQUEST, request=request)
    except TranslationError as exc:
        status_code = 503 if exc.code == "TRANSLATE_NOT_CONFIGURED" else 400
        if exc.code == "TRANSLATE_FAILED":
            status_code = 502
        if exc.code == "PREVIEW_EXTRACT_EMPTY":
            status_code = 400
        return error_response(exc.code, exc.message, status=status_code, request=request)

    return success_response(
        {
            "translated_text": result.get("translated_text", ""),
            "source_text": result.get("source_text", ""),
            "truncated": result.get("truncated", False),
            "extraction_method": result.get("extraction_method", ""),
            "page_count": result.get("page_count", 0),
            "processed_pages": result.get("processed_pages", 0),
            "char_count": result.get("char_count", 0),
        },
        request=request,
    )


def _download_project_file(request, project, file_id):
    from django.http import FileResponse

    pf = get_object_or_404(ProjectFile, pk=file_id, project=project)
    if not _user_can_access_project_file(request.user, project, pf):
        return error_response(
            "PROJECT_FILE_FORBIDDEN",
            "无权访问该文件",
            status=status.HTTP_403_FORBIDDEN,
            request=request,
        )
    if not pf.file:
        return error_response("PROJECT_FILE_MISSING", "文件不存在", request=request)
    return FileResponse(pf.file.open("rb"), as_attachment=False, filename=pf.file_name)


class MemberProjectFileListView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk, buyer=request.user)
        files = project.files.filter(visibility="all").select_related("uploader", "stage")
        return success_response(
            {"items": ProjectFileSerializer(files, many=True, context={"request": request}).data},
            request=request,
        )


class MemberProjectFileDownloadView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk, file_id):
        project = get_object_or_404(Project, pk=pk, buyer=request.user)
        return _download_project_file(request, project, file_id)


class MemberProjectFilePreviewPdfView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk, file_id):
        project = get_object_or_404(Project, pk=pk, buyer=request.user)
        return _preview_project_file_pdf(request, project, file_id)


class MemberProjectFileTranslateView(APIView):
    permission_classes = [IsBuyerRole]

    def post(self, request, pk, file_id):
        project = get_object_or_404(Project, pk=pk, buyer=request.user)
        return _translate_project_file_response(request, project, file_id)


class SupplierProjectFileListCreateView(APIView):
    permission_classes = [IsSupplierRole]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        files = project.files.select_related("uploader", "stage")
        return success_response(
            {"items": ProjectFileSerializer(files, many=True, context={"request": request}).data},
            request=request,
        )

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        pf, err = _create_project_file(
            request,
            project,
            default_visibility="all",
            fallback_current_stage=True,
        )
        if err:
            return err
        return success_response(
            ProjectFileSerializer(pf, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class SupplierProjectFileDownloadView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk, file_id):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        return _download_project_file(request, project, file_id)


class SupplierProjectFilePreviewPdfView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk, file_id):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        return _preview_project_file_pdf(request, project, file_id)


class SupplierProjectFileTranslateView(APIView):
    permission_classes = [IsSupplierRole]

    def post(self, request, pk, file_id):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        return _translate_project_file_response(request, project, file_id)


class SupplierProjectFileDeleteView(APIView):
    permission_classes = [IsSupplierRole]

    def delete(self, request, pk, file_id):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        pf = get_object_or_404(ProjectFile, pk=file_id, project=project)
        cleanup_preview_cache(pf.id)
        pf.file.delete(save=False)
        pf.delete()
        return success_response({}, message="文件已删除", request=request)


class AdminProjectFileListCreateView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        files = project.files.select_related("uploader", "stage")
        return success_response(
            {"items": ProjectFileSerializer(files, many=True, context={"request": request}).data},
            request=request,
        )

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        pf, err = _create_project_file(request, project)
        if err:
            return err
        return success_response(
            ProjectFileSerializer(pf, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminProjectFileDownloadView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk, file_id):
        project = get_object_or_404(Project, pk=pk)
        return _download_project_file(request, project, file_id)


class AdminProjectFileDeleteView(APIView):
    permission_classes = [IsAdminRole]

    def delete(self, request, pk, file_id):
        project = get_object_or_404(Project, pk=pk)
        pf = get_object_or_404(ProjectFile, pk=file_id, project=project)
        cleanup_preview_cache(pf.id)
        pf.file.delete(save=False)
        pf.delete()
        return success_response({}, message="文件已删除", request=request)


class DefectReportTemplateDownloadView(APIView):
    """下载不良报告 Word 模板。"""

    permission_classes = [IsAuthenticatedPlatformUser]

    def get(self, request):
        from django.http import FileResponse, Http404

        from apps.project.defect_template import get_defect_report_template_path

        try:
            path = get_defect_report_template_path()
        except FileNotFoundError as exc:
            raise Http404(str(exc)) from exc
        response = FileResponse(
            path.open("rb"),
            as_attachment=True,
            filename="defect_report_template.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        return response
