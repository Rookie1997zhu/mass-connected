from rest_framework import serializers

from apps.contract.models import Contract


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
