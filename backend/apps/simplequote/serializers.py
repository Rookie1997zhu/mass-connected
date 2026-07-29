from rest_framework import serializers

from apps.simplequote.models import (
    DielineCategory,
    DielineTemplate,
    DielineTemplateAsset,
    Print3dSliceJob,
    QuoteParam,
    QuoteTable,
    SimpleQuote,
)


class QuoteTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteTable
        fields = [
            "id",
            "quote_type",
            "table_key",
            "rows",
            "is_active",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class SimpleQuoteSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = SimpleQuote
        fields = [
            "id",
            "quote_no",
            "quote_type",
            "product_name",
            "inputs",
            "result",
            "total_amount",
            "currency",
            "status",
            "valid_until",
            "points_spent",
            "pdf_url",
            "converted_rfq",
            "created_at",
        ]
        read_only_fields = fields

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if obj.pdf and request:
            return request.build_absolute_uri(obj.pdf.url)
        return obj.pdf.url if obj.pdf else ""


class SimpleQuoteListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimpleQuote
        fields = [
            "id",
            "quote_no",
            "quote_type",
            "product_name",
            "total_amount",
            "currency",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class SimpleQuoteCreateSerializer(serializers.Serializer):
    quote_type = serializers.ChoiceField(
        choices=["injection", "print3d", "pcba", "pcb", "software", "ic", "paper_box"]
    )
    product_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    # currency 一般由服务端按报价类型决定（注塑=CNY），此处仅作前向兼容可选入参。
    currency = serializers.CharField(max_length=3, required=False, allow_blank=True)
    inputs = serializers.DictField(required=False, default=dict)


class Print3dSliceJobSerializer(serializers.ModelSerializer):
    preview_url = serializers.SerializerMethodField()

    class Meta:
        model = Print3dSliceJob
        fields = [
            "id",
            "status",
            "original_filename",
            "file_ext",
            "inputs",
            "result",
            "preview_url",
            "error_code",
            "error_message",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_preview_url(self, obj):
        if not obj.preview_file:
            return None
        return f"/api/member/simple-quotes/print3d/slice-jobs/{obj.pk}/preview"


class Print3dSliceJobCreateSerializer(serializers.Serializer):
    """会员创建切片任务；打印机由服务端按管理端默认配置决定，不接收该字段。"""

    material = serializers.CharField(max_length=64, default="PLA")
    quality = serializers.CharField(max_length=64, default="standard")
    infill_density = serializers.IntegerField(required=False, min_value=5, max_value=100)
    support = serializers.BooleanField(required=False, default=False)
    quantity = serializers.IntegerField(required=False, min_value=1, default=1)
    post_process = serializers.CharField(max_length=64, required=False, default="none")
    rush = serializers.BooleanField(required=False, default=False)


class AdminPrint3dConfigSerializer(serializers.Serializer):
    params = serializers.DictField(required=False)
    materials = serializers.ListField(child=serializers.DictField(), required=False)
    printers = serializers.ListField(child=serializers.DictField(), required=False)
    qualities = serializers.ListField(child=serializers.DictField(), required=False)
    post_processing = serializers.ListField(child=serializers.DictField(), required=False)


class QuoteParamSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteParam
        fields = [
            "id",
            "quote_type",
            "param_key",
            "label",
            "value",
            "unit",
            "note",
            "is_active",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class DielineCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DielineCategory
        fields = [
            "id",
            "code",
            "name_i18n",
            "desc_i18n",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def _parse_json_field(self, value):
        if isinstance(value, str):
            import json

            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return value or {}

    def validate_name_i18n(self, value):
        return self._parse_json_field(value)

    def validate_desc_i18n(self, value):
        return self._parse_json_field(value)

    def validate_code(self, value):
        code = str(value or "").strip()
        if not code:
            raise serializers.ValidationError("分类编码不能为空")
        return code


class DielineTemplateSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    production_asset_url = serializers.SerializerMethodField()
    parametric_asset_status = serializers.SerializerMethodField()
    active_parametric_asset = serializers.SerializerMethodField()
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=DielineCategory.objects.all(),
        source="category",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = DielineTemplate
        fields = [
            "id",
            "code",
            "category_id",
            "category_code",
            "engine_key",
            "name_i18n",
            "desc_i18n",
            "default_length_mm",
            "default_width_mm",
            "default_height_mm",
            "default_manufacturing_length_mm",
            "default_manufacturing_width_mm",
            "default_manufacturing_height_mm",
            "default_internal_length_mm",
            "default_internal_width_mm",
            "default_internal_height_mm",
            "default_external_length_mm",
            "default_external_width_mm",
            "default_external_height_mm",
            "default_thickness_mm",
            "default_glue_tab_mm",
            "flute_type",
            "material_type",
            "default_dimension_type",
            "min_length_mm",
            "max_length_mm",
            "min_width_mm",
            "max_width_mm",
            "min_height_mm",
            "max_height_mm",
            "slot_gap_mm",
            "crease_gap_mm",
            "flap_gap_mm",
            "structure_params",
            "allowances",
            "production_asset",
            "production_asset_url",
            "parametric_asset_status",
            "active_parametric_asset",
            "priority",
            "quote_enabled",
            "preview_enabled",
            "sort_order",
            "is_active",
            "thumbnail",
            "thumbnail_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "thumbnail_url",
            "production_asset_url",
            "parametric_asset_status",
            "active_parametric_asset",
            "created_at",
            "updated_at",
        ]

    def _parse_json_field(self, value):
        if isinstance(value, str):
            import json

            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return value or {}

    def validate_name_i18n(self, value):
        return self._parse_json_field(value)

    def validate_desc_i18n(self, value):
        return self._parse_json_field(value)

    def validate_allowances(self, value):
        return self._parse_json_field(value)

    def validate_structure_params(self, value):
        return self._parse_json_field(value)

    def validate(self, attrs):
        category = attrs.get("category")
        category_code = attrs.get("category_code")
        if category is not None:
            attrs["category_code"] = category.code
        elif category_code:
            category_code = str(category_code).strip()
            attrs["category_code"] = category_code
            category = DielineCategory.objects.filter(code=category_code).first()
            if not category:
                raise serializers.ValidationError(
                    {"category_code": "分类不存在，请先在分类管理中创建"}
                )
            attrs["category"] = category
        elif self.instance and self.instance.category_id:
            attrs["category"] = self.instance.category
            attrs["category_code"] = self.instance.category_code
        else:
            raise serializers.ValidationError({"category_code": "必须选择分类"})

        mfg_l = attrs.get("default_manufacturing_length_mm")
        mfg_w = attrs.get("default_manufacturing_width_mm")
        mfg_h = attrs.get("default_manufacturing_height_mm")
        if mfg_l is not None:
            attrs["default_length_mm"] = mfg_l
        if mfg_w is not None:
            attrs["default_width_mm"] = mfg_w
        if mfg_h is not None:
            attrs["default_height_mm"] = mfg_h

        min_l = attrs.get("min_length_mm")
        max_l = attrs.get("max_length_mm")
        if min_l is not None and max_l is not None and min_l > max_l:
            raise serializers.ValidationError({"min_length_mm": "最小长不能大于最大长"})
        min_w = attrs.get("min_width_mm")
        max_w = attrs.get("max_width_mm")
        if min_w is not None and max_w is not None and min_w > max_w:
            raise serializers.ValidationError({"min_width_mm": "最小宽不能大于最大宽"})
        min_h = attrs.get("min_height_mm")
        max_h = attrs.get("max_height_mm")
        if min_h is not None and max_h is not None and min_h > max_h:
            raise serializers.ValidationError({"min_height_mm": "最小高不能大于最大高"})

        instance = self.instance
        enabling_flags = any(
            attrs.get(flag) if flag in attrs else (getattr(instance, flag) if instance else False)
            for flag in ("is_active", "preview_enabled", "quote_enabled")
        )
        if enabling_flags:
            has_mapped_asset = False
            if instance is not None:
                has_mapped_asset = instance.assets.filter(
                    is_active=True,
                    mapping_status="mapped",
                ).exists()
            if not has_mapped_asset:
                from core.exceptions import AppAPIException

                raise AppAPIException(
                    detail="模板须上传 DXF/SVG 并完成映射激活后，才可对用户开放预览或报价",
                    code="DIELINE_TEMPLATE_ASSET_REQUIRED",
                )
        return attrs

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        if obj.thumbnail and request:
            return request.build_absolute_uri(obj.thumbnail.url)
        return obj.thumbnail.url if obj.thumbnail else ""

    def get_production_asset_url(self, obj):
        request = self.context.get("request")
        if obj.production_asset and request:
            return request.build_absolute_uri(obj.production_asset.url)
        return obj.production_asset.url if obj.production_asset else ""

    def get_parametric_asset_status(self, obj):
        asset = obj.assets.filter(is_active=True).first()
        if asset:
            return asset.mapping_status
        if obj.assets.exists():
            return "draft"
        return "none"

    def get_active_parametric_asset(self, obj):
        asset = obj.assets.filter(is_active=True, mapping_status="mapped").first()
        if not asset:
            return None
        return DielineTemplateAssetSerializer(asset, context=self.context).data


class DielineTemplateAssetSerializer(serializers.ModelSerializer):
    source_file_url = serializers.SerializerMethodField()

    class Meta:
        model = DielineTemplateAsset
        fields = [
            "id",
            "template",
            "source_file",
            "source_file_url",
            "source_format",
            "parsed_geometry",
            "mapping_schema",
            "base_dimensions",
            "mapping_status",
            "parse_errors",
            "version",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "source_file_url",
            "source_format",
            "parsed_geometry",
            "mapping_status",
            "parse_errors",
            "version",
            "created_at",
            "updated_at",
        ]

    def _parse_json_field(self, value):
        if isinstance(value, str):
            import json

            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return value or {}

    def validate_mapping_schema(self, value):
        parsed = self._parse_json_field(value)
        if parsed and not parsed.get("entity_roles"):
            raise serializers.ValidationError("mapping_schema 必须包含 entity_roles")
        return parsed

    def validate_base_dimensions(self, value):
        parsed = self._parse_json_field(value)
        if not parsed:
            return {}
        for key in ("length", "width", "height"):
            try:
                number = float(parsed.get(key, 0))
            except (TypeError, ValueError):
                raise serializers.ValidationError(f"{key} 必须为数字")
            if number <= 0:
                raise serializers.ValidationError(f"{key} 必须大于 0")
        if "thickness" in parsed and parsed.get("thickness") not in (None, ""):
            try:
                thickness = float(parsed.get("thickness"))
            except (TypeError, ValueError):
                raise serializers.ValidationError("thickness 必须为数字")
            if thickness < 0:
                raise serializers.ValidationError("thickness 不能小于 0")
        return parsed

    def get_source_file_url(self, obj):
        request = self.context.get("request")
        if obj.source_file and request:
            return request.build_absolute_uri(obj.source_file.url)
        return obj.source_file.url if obj.source_file else ""
