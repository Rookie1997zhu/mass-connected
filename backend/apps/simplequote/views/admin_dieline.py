from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.simplequote.dieline_import import (
    DielineImportError,
    default_mapping_schema,
    parse_uploaded_dieline,
    source_format_from_name,
)
from apps.simplequote.models import (
    DielineCategory,
    DielineTemplate,
    DielineTemplateAsset,
)
from apps.simplequote.serializers import (
    DielineCategorySerializer,
    DielineTemplateAssetSerializer,
    DielineTemplateSerializer,
)
from core.permissions import IsAdminRole
from core.responses import error_response, success_response


class AdminDielineCategoryView(APIView):
    """刀版盒型分类（管理员维护）。"""

    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = DielineCategory.objects.all().order_by("sort_order", "code")
        return success_response(
            {"items": DielineCategorySerializer(qs, many=True).data},
            request=request,
        )

    def post(self, request):
        serializer = DielineCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminDielineCategoryDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        category = get_object_or_404(DielineCategory, pk=pk)
        serializer = DielineCategorySerializer(
            category, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)

    def delete(self, request, pk):
        category = get_object_or_404(DielineCategory, pk=pk)
        if category.templates.exists():
            return error_response(
                "DIELINE_CATEGORY_IN_USE",
                "该分类下仍有模板，无法删除。请先迁移或删除模板，或停用分类。",
                request=request,
            )
        category.delete()
        return success_response({"id": pk}, message="已删除", request=request)


class AdminDielineTemplateView(APIView):
    """刀版参数化模板库（管理员维护）。"""

    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        qs = DielineTemplate.objects.all().order_by("sort_order", "code")
        return success_response(
            {
                "items": DielineTemplateSerializer(
                    qs, many=True, context={"request": request}
                ).data
            },
            request=request,
        )

    def post(self, request):
        serializer = DielineTemplateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminDielineTemplateDetailView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        template = get_object_or_404(DielineTemplate, pk=pk)
        serializer = DielineTemplateSerializer(
            template, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)

    def delete(self, request, pk):
        template = get_object_or_404(DielineTemplate, pk=pk)
        template.delete()
        return success_response({"id": pk}, message="已删除", request=request)


MAX_DIELINE_ASSET_SIZE = 20 * 1024 * 1024
ALLOWED_DIELINE_ASSET_EXT = ("dxf", "svg", "ai", "pdf")


class AdminDielineTemplateAssetView(APIView):
    """刀版模板资产版本：上传真实 DXF/SVG 并保存解析 JSON。"""

    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, template_id):
        template = get_object_or_404(DielineTemplate, pk=template_id)
        qs = template.assets.all()
        return success_response(
            {"items": DielineTemplateAssetSerializer(qs, many=True, context={"request": request}).data},
            request=request,
        )

    def post(self, request, template_id):
        template = get_object_or_404(DielineTemplate, pk=template_id)
        upload = request.FILES.get("source_file")
        if not upload:
            return error_response("DIELINE_ASSET_FILE_REQUIRED", "请上传刀版文件", request=request)
        if upload.size > MAX_DIELINE_ASSET_SIZE:
            return error_response("DIELINE_ASSET_TOO_LARGE", "文件超过 20MB 上限", request=request)
        source_format = source_format_from_name(upload.name)
        if source_format not in ALLOWED_DIELINE_ASSET_EXT:
            return error_response("DIELINE_ASSET_FORMAT_INVALID", "仅支持 DXF/SVG/AI/PDF 文件", request=request)

        latest = template.assets.order_by("-version").first()
        version = (latest.version if latest else 0) + 1
        try:
            base_dimensions = {
                "length": float(request.data.get("base_length") or template.default_length_mm),
                "width": float(request.data.get("base_width") or template.default_width_mm),
                "height": float(request.data.get("base_height") or template.default_height_mm),
                "thickness": float(request.data.get("base_thickness") or template.default_thickness_mm),
            }
        except (TypeError, ValueError):
            return error_response(
                "DIELINE_ASSET_BASE_DIMENSIONS_INVALID",
                "基准尺寸必须为数字",
                request=request,
            )
        if min(base_dimensions.values()) <= 0:
            return error_response(
                "DIELINE_ASSET_BASE_DIMENSIONS_INVALID",
                "基准尺寸必须大于 0",
                request=request,
            )
        asset = DielineTemplateAsset.objects.create(
            template=template,
            source_file=upload,
            source_format=source_format,
            base_dimensions=base_dimensions,
            version=version,
            mapping_status="uploaded",
        )
        if source_format in {"ai", "pdf"}:
            asset.mapping_status = "attachment_only"
            asset.parse_errors = {
                "message": "AI/PDF 已保存为附件；参数化映射请上传 DXF/SVG 文件。"
            }
            asset.save(update_fields=["mapping_status", "parse_errors", "updated_at"])
            return success_response(
                DielineTemplateAssetSerializer(asset, context={"request": request}).data,
                message="附件已保存，需 DXF/SVG 才能参数化",
                status=status.HTTP_201_CREATED,
                request=request,
            )

        try:
            upload.seek(0)
            parsed_geometry = parse_uploaded_dieline(upload, source_format)
            asset.parsed_geometry = parsed_geometry
            asset.mapping_schema = default_mapping_schema(parsed_geometry, base_dimensions)
            asset.mapping_status = "parsed"
            asset.parse_errors = {}
            asset.save(update_fields=["parsed_geometry", "mapping_schema", "mapping_status", "parse_errors", "updated_at"])
        except (DielineImportError, ValueError) as exc:
            asset.mapping_status = "failed"
            asset.parse_errors = {"message": str(exc)}
            asset.save(update_fields=["mapping_status", "parse_errors", "updated_at"])
            return error_response(
                "DIELINE_ASSET_PARSE_FAILED",
                "刀版文件解析失败",
                errors=asset.parse_errors,
                request=request,
            )

        return success_response(
            DielineTemplateAssetSerializer(asset, context={"request": request}).data,
            message="解析成功",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminDielineTemplateAssetDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, template_id, asset_id):
        template = get_object_or_404(DielineTemplate, pk=template_id)
        asset = get_object_or_404(DielineTemplateAsset, pk=asset_id, template=template)
        serializer = DielineTemplateAssetSerializer(
            asset,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(mapping_status="mapped")
        return success_response(serializer.data, message="映射已保存", request=request)

    def delete(self, request, template_id, asset_id):
        template = get_object_or_404(DielineTemplate, pk=template_id)
        asset = get_object_or_404(DielineTemplateAsset, pk=asset_id, template=template)
        asset.delete()
        return success_response({"id": asset_id}, message="已删除", request=request)


class AdminDielineTemplateAssetActivateView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, template_id, asset_id):
        template = get_object_or_404(DielineTemplate, pk=template_id)
        asset = get_object_or_404(DielineTemplateAsset, pk=asset_id, template=template)
        if asset.mapping_status != "mapped":
            return error_response("DIELINE_ASSET_NOT_MAPPED", "请先保存映射后再启用", request=request)
        with transaction.atomic():
            template.assets.exclude(pk=asset.pk).update(is_active=False)
            asset.is_active = True
            asset.save(update_fields=["is_active", "updated_at"])
        return success_response(
            DielineTemplateAssetSerializer(asset, context={"request": request}).data,
            message="已启用",
            request=request,
        )
