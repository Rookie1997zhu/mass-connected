from rest_framework import serializers

from apps.contract.models import Contract, NdaSignature, NdaTemplate


class ContractSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    supplier_name = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            "id",
            "contract_no",
            "title",
            "rfq",
            "amount",
            "currency",
            "status",
            "supplier_name",
            "pdf_url",
            "signed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if obj.pdf and request:
            return request.build_absolute_uri(obj.pdf.url)
        return obj.pdf.url if obj.pdf else ""

    def get_supplier_name(self, obj):
        if not obj.supplier_id:
            return ""
        profile = getattr(obj.supplier, "factory_profile", None)
        return profile.company_name if profile else (obj.supplier.name or obj.supplier.email)


class AdminContractSerializer(ContractSerializer):
    buyer_email = serializers.EmailField(source="buyer.email", read_only=True)

    class Meta(ContractSerializer.Meta):
        fields = ContractSerializer.Meta.fields + ["buyer", "buyer_email"]
        read_only_fields = fields


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
