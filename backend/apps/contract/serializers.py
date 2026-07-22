from rest_framework import serializers

from apps.contract.models import Contract, NdaSignature, NdaTemplate

SIGNATURE_MAX_BYTES = 2 * 1024 * 1024
SIGNATURE_ALLOWED_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


class ContractSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    signature_image_url = serializers.SerializerMethodField()
    supplier_name = serializers.SerializerMethodField()
    rfq_no = serializers.CharField(source="rfq.rfq_no", read_only=True, default="")
    quote_request_id = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            "id",
            "contract_no",
            "title",
            "rfq",
            "rfq_no",
            "quote_request_id",
            "amount",
            "currency",
            "status",
            "supplier_name",
            "rendered_body",
            "company_name",
            "business_reg_no",
            "company_address",
            "signer_name",
            "pdf_url",
            "signature_image_url",
            "agree_at",
            "signed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if obj.pdf and request:
            return request.build_absolute_uri(obj.pdf.url)
        return obj.pdf.url if obj.pdf else ""

    def get_signature_image_url(self, obj):
        request = self.context.get("request")
        if obj.signature_image and request:
            return request.build_absolute_uri(obj.signature_image.url)
        return obj.signature_image.url if obj.signature_image else ""

    def get_supplier_name(self, obj):
        if not obj.supplier_id:
            return ""
        profile = getattr(obj.supplier, "factory_profile", None)
        return profile.company_name if profile else (obj.supplier.name or obj.supplier.email)

    def get_quote_request_id(self, obj):
        if obj.quote_id:
            return getattr(obj.quote, "quote_request_id", None)
        po = getattr(obj, "production_order", None)
        if po and po.quote_id:
            return getattr(po.quote, "quote_request_id", None)
        return None


class AdminContractSerializer(ContractSerializer):
    buyer_email = serializers.EmailField(source="buyer.email", read_only=True)

    class Meta(ContractSerializer.Meta):
        fields = ContractSerializer.Meta.fields + ["buyer", "buyer_email"]
        read_only_fields = fields


class ContractSignSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=200)
    business_reg_no = serializers.CharField(max_length=64)
    company_address = serializers.CharField(max_length=300)
    signer_name = serializers.CharField(max_length=120)
    agree = serializers.BooleanField()
    signature_image = serializers.ImageField()

    def validate_agree(self, value):
        if not value:
            raise serializers.ValidationError("须同意保密协议条款")
        return value

    def validate_signature_image(self, value):
        if not value:
            raise serializers.ValidationError("请上传签名图片")
        content_type = getattr(value, "content_type", "") or ""
        if content_type and content_type.lower() not in SIGNATURE_ALLOWED_TYPES:
            raise serializers.ValidationError("签名图片仅支持 JPG / PNG / WEBP")
        if value.size and value.size > SIGNATURE_MAX_BYTES:
            raise serializers.ValidationError("签名图片大小不能超过 2MB")
        return value


class NdaTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NdaTemplate
        fields = ["id", "version", "title", "body", "effective_date", "is_active"]
        read_only_fields = fields


class NdaSignatureSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    template_version = serializers.CharField(source="template.version", read_only=True)

    class Meta:
        model = NdaSignature
        fields = [
            "id",
            "company_name",
            "status",
            "template_version",
            "signed_at",
            "retention_delete_at",
            "pdf_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if obj.pdf and request:
            return request.build_absolute_uri(obj.pdf.url)
        return obj.pdf.url if obj.pdf else ""


class NdaSignSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    agree = serializers.BooleanField(default=False)

    def validate_agree(self, value):
        if not value:
            raise serializers.ValidationError("须同意保密协议条款")
        return value
