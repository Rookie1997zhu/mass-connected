from rest_framework import serializers

from apps.project.models import (
    Project,
    ProjectFile,
    ProjectIssue,
    ProjectStage,
    ProjectTodo,
    ProjectUpdate,
)
from apps.project.services import get_current_stage


PREVIEWABLE_EXTS = {"xlsx", "xls", "csv", "jpg", "jpeg", "png", "gif", "webp", "pdf"}


class ProjectFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    uploader_name = serializers.SerializerMethodField()
    stage_id = serializers.IntegerField(source="stage.id", read_only=True, allow_null=True)
    stage_name = serializers.CharField(source="stage.name", read_only=True, allow_null=True)
    file_ext = serializers.SerializerMethodField()
    is_previewable = serializers.SerializerMethodField()

    class Meta:
        model = ProjectFile
        fields = [
            "id",
            "file_name",
            "file_category",
            "visibility",
            "file_url",
            "uploader_name",
            "stage_id",
            "stage_name",
            "file_ext",
            "is_previewable",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "file_url",
            "uploader_name",
            "stage_id",
            "stage_name",
            "file_ext",
            "is_previewable",
            "created_at",
        ]

    def get_file_ext(self, obj):
        name = obj.file_name or ""
        if "." not in name:
            return ""
        return name.rsplit(".", 1)[-1].lower()

    def get_is_previewable(self, obj):
        return self.get_file_ext(obj) in PREVIEWABLE_EXTS

    def get_file_url(self, obj):
        """返回鉴权下载接口，避免直接暴露公开 /media URL。"""
        request = self.context.get("request")
        if not request or not obj.pk:
            return ""
        project = obj.project
        user = request.user
        if getattr(user, "role", "") == "admin":
            path = f"/api/admin/projects/{project.id}/files/{obj.id}/download"
        elif project.supplier_id == user.id:
            path = f"/api/supplier/projects/{project.id}/files/{obj.id}/download"
        else:
            path = f"/api/member/projects/{project.id}/files/{obj.id}/download"
        return request.build_absolute_uri(path)

    def get_uploader_name(self, obj):
        if not obj.uploader_id:
            return "平台"
        return obj.uploader.name or obj.uploader.email


class ProjectStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStage
        fields = [
            "id",
            "name",
            "sort_order",
            "status",
            "planned_date",
            "started_at",
            "completed_at",
        ]
        read_only_fields = ["id", "started_at", "completed_at"]


class ProjectUpdateSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectUpdate
        fields = [
            "id",
            "stage",
            "author_name",
            "content",
            "is_customer_visible",
            "created_at",
        ]
        read_only_fields = ["id", "author_name", "created_at"]

    def get_author_name(self, obj):
        if not obj.author_id:
            return "平台"
        return obj.author.name or obj.author.email


class ProjectTodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTodo
        fields = ["id", "title", "assignee_type", "is_done", "due_date", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProjectTodoAggregateSerializer(ProjectTodoSerializer):
    project_id = serializers.IntegerField(source="project.id", read_only=True)
    project_no = serializers.CharField(source="project.project_no", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)

    class Meta(ProjectTodoSerializer.Meta):
        fields = ProjectTodoSerializer.Meta.fields + ["project_id", "project_no", "project_title"]
        read_only_fields = fields


class ProjectIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectIssue
        fields = [
            "id",
            "title",
            "description",
            "severity",
            "status",
            "created_at",
            "resolved_at",
        ]
        read_only_fields = ["id", "status", "created_at", "resolved_at"]


class ProjectListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()
    current_stage = serializers.SerializerMethodField()
    rfq = serializers.IntegerField(source="rfq_id", read_only=True, allow_null=True)
    rfq_no = serializers.CharField(source="rfq.rfq_no", read_only=True, default="")
    quote_request_id = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "project_no",
            "title",
            "status",
            "progress_percent",
            "amount",
            "currency",
            "supplier_name",
            "current_stage",
            "rfq",
            "rfq_no",
            "quote_request_id",
            "expected_delivery_date",
            "created_at",
        ]
        read_only_fields = fields

    def get_supplier_name(self, obj):
        if not obj.supplier_id:
            return ""
        profile = getattr(obj.supplier, "factory_profile", None)
        return profile.company_name if profile else (obj.supplier.name or obj.supplier.email)

    def get_current_stage(self, obj):
        stage = get_current_stage(obj)
        if not stage:
            return None
        return {"id": stage.id, "name": stage.name, "status": stage.status, "sort_order": stage.sort_order}

    def get_quote_request_id(self, obj):
        po = getattr(obj, "production_order", None)
        if po and po.quote_id:
            return getattr(po.quote, "quote_request_id", None)
        return None


class ProjectDetailSerializer(ProjectListSerializer):
    stages = ProjectStageSerializer(many=True, read_only=True)
    updates = serializers.SerializerMethodField()
    todos = ProjectTodoSerializer(many=True, read_only=True)
    issues = ProjectIssueSerializer(many=True, read_only=True)
    files = serializers.SerializerMethodField()
    production_order_id = serializers.IntegerField(
        source="production_order.id", read_only=True, allow_null=True
    )
    production_order_no = serializers.CharField(
        source="production_order.order_no", read_only=True, default=""
    )

    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + [
            "production_order_id",
            "production_order_no",
            "stages",
            "updates",
            "todos",
            "issues",
            "files",
        ]
        read_only_fields = fields

    def get_files(self, obj):
        files = obj.files.select_related("stage", "uploader").all()
        customer_only = self.context.get("customer_only", False)
        if customer_only:
            files = [f for f in files if f.visibility == "all"]
        return ProjectFileSerializer(files, many=True, context=self.context).data

    def get_updates(self, obj):
        customer_only = self.context.get("customer_only", False)
        updates = obj.updates.all()
        if customer_only:
            updates = [u for u in updates if u.is_customer_visible]
        return ProjectUpdateSerializer(updates, many=True).data
