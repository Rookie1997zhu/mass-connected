from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
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
from apps.project.services import recalc_progress
from core.file_validation import validate_upload_file
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response


class MemberProjectListView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Project.objects.filter(buyer=request.user).select_related("supplier").order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ProjectListSerializer(page, many=True).data)


class MemberProjectDetailView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        project = get_object_or_404(
            Project.objects.prefetch_related("stages", "updates", "todos", "issues", "files"),
            pk=pk,
            buyer=request.user,
        )
        return success_response(
            ProjectDetailSerializer(project, context={"customer_only": True}).data,
            request=request,
        )


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
        qs = Project.objects.filter(supplier=request.user).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ProjectListSerializer(page, many=True).data)


class SupplierProjectDetailView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk):
        project = get_object_or_404(
            Project.objects.prefetch_related("stages", "updates", "todos", "issues", "files"),
            pk=pk,
            supplier=request.user,
        )
        return success_response(ProjectDetailSerializer(project).data, request=request)


class SupplierProjectUpdateCreateView(APIView):
    permission_classes = [IsSupplierRole]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        content = request.data.get("content", "").strip()
        if not content:
            return error_response("PROJECT_UPDATE_CONTENT_REQUIRED", "进度内容不能为空", request=request)
        update = ProjectUpdate.objects.create(
            project=project,
            stage_id=request.data.get("stage") or None,
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
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        stage = get_object_or_404(ProjectStage, pk=stage_id, project=project)
        new_status = request.data.get("status")
        if new_status not in {"pending", "in_progress", "completed"}:
            return error_response("PROJECT_STAGE_STATUS_INVALID", "无效的阶段状态", request=request)
        stage.status = new_status
        if new_status == "in_progress" and not stage.started_at:
            stage.started_at = timezone.now()
        if new_status == "completed" and not stage.completed_at:
            stage.completed_at = timezone.now()
        stage.save(update_fields=["status", "started_at", "completed_at"])
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
            Project.objects.prefetch_related("stages", "updates", "todos", "issues"),
            pk=pk,
        )
        return success_response(ProjectDetailSerializer(project).data, request=request)

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


def _create_project_file(request, project, default_visibility="all"):
    file_obj = request.FILES.get("file")
    code, msg = validate_upload_file(file_obj)
    if code:
        return None, error_response(code, msg, request=request)
    pf = ProjectFile.objects.create(
        project=project,
        uploader=request.user,
        file=file_obj,
        file_name=file_obj.name,
        file_category=request.data.get("file_category", "other"),
        visibility=request.data.get("visibility", default_visibility),
    )
    return pf, None


class MemberProjectFileListView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk, buyer=request.user)
        files = project.files.filter(visibility="all").select_related("uploader")
        return success_response(
            {"items": ProjectFileSerializer(files, many=True, context={"request": request}).data},
            request=request,
        )


class SupplierProjectFileListCreateView(APIView):
    permission_classes = [IsSupplierRole]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        files = project.files.select_related("uploader")
        return success_response(
            {"items": ProjectFileSerializer(files, many=True, context={"request": request}).data},
            request=request,
        )

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, supplier=request.user)
        pf, err = _create_project_file(request, project)
        if err:
            return err
        return success_response(
            ProjectFileSerializer(pf, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminProjectFileListCreateView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        files = project.files.select_related("uploader")
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


class AdminProjectFileDeleteView(APIView):
    permission_classes = [IsAdminRole]

    def delete(self, request, pk, file_id):
        project = get_object_or_404(Project, pk=pk)
        pf = get_object_or_404(ProjectFile, pk=file_id, project=project)
        pf.file.delete(save=False)
        pf.delete()
        return success_response({}, message="文件已删除", request=request)
