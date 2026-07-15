from rest_framework import serializers

from apps.accounts.models import FactoryProfile, SupplierAttachment, SupplierTag, User

PREVIEWABLE_EXTS = {"xlsx", "xls", "csv", "jpg", "jpeg", "png", "gif", "webp", "pdf"}
PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES = {
    "company_profile",
    "certification",
    "equipment",
    "case",
}


class FactoryProfileSummarySerializer(serializers.ModelSerializer):
    business_license_url = serializers.SerializerMethodField()

    class Meta:
        model = FactoryProfile
        fields = [
            "id",
            "company_name",
            "short_name",
            "region",
            "country",
            "city",
            "intro",
            "contact_phone",
            "payment_terms",
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
            "status",
            "business_license_url",
        ]
        read_only_fields = fields

    def get_business_license_url(self, obj):
        request = self.context.get("request")
        if not obj.business_license:
            return ""
        url = obj.business_license.url
        return request.build_absolute_uri(url) if request else url


class MemberEnterpriseProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FactoryProfile
        fields = [
            "company_name",
            "short_name",
            "region",
            "country",
            "city",
            "intro",
            "contact_phone",
            "payment_terms",
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
        ]


class SupplierTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierTag
        fields = ["id", "tag_name"]
        read_only_fields = ["id"]


class SupplierAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    is_previewable = serializers.SerializerMethodField()

    class Meta:
        model = SupplierAttachment
        fields = [
            "id",
            "file_name",
            "category",
            "is_public",
            "file_url",
            "file_ext",
            "is_previewable",
            "uploaded_at",
        ]
        read_only_fields = fields

    def get_file_ext(self, obj):
        name = obj.file_name or ""
        if "." not in name:
            return ""
        return name.rsplit(".", 1)[-1].lower()

    def get_is_previewable(self, obj):
        return self.get_file_ext(obj) in PREVIEWABLE_EXTS

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not request or not obj.pk:
            return ""
        role = getattr(request.user, "role", "")
        if role in {"super_admin", "operator", "sales"} or getattr(request.user, "is_staff", False):
            path = f"/api/admin/suppliers/{obj.profile_id}/attachments/{obj.id}/download"
        else:
            path = f"/api/supplier/profile/attachments/{obj.id}/download"
        return request.build_absolute_uri(path)


class PublicSupplierAttachmentSerializer(serializers.ModelSerializer):
    """买家可见的公开企业资料附件（不含敏感字段）。"""

    file_url = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    is_previewable = serializers.SerializerMethodField()

    class Meta:
        model = SupplierAttachment
        fields = [
            "id",
            "file_name",
            "category",
            "file_url",
            "file_ext",
            "is_previewable",
            "uploaded_at",
        ]
        read_only_fields = fields

    def get_file_ext(self, obj):
        name = obj.file_name or ""
        if "." not in name:
            return ""
        return name.rsplit(".", 1)[-1].lower()

    def get_is_previewable(self, obj):
        return self.get_file_ext(obj) in PREVIEWABLE_EXTS

    def get_file_url(self, obj):
        request = self.context.get("request")
        quote_id = self.context.get("quote_id")
        rfq_id = self.context.get("rfq_id")
        if not request or not obj.pk or not quote_id or not rfq_id:
            return ""
        path = (
            f"/api/member/rfqs/{rfq_id}/quotes/{quote_id}/supplier-attachments/{obj.id}/download"
        )
        return request.build_absolute_uri(path)


class PublicSupplierProfileSerializer(serializers.ModelSerializer):
    """买家甄别用公开企业资料：不含联系方式与营业执照。"""

    process_names = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    public_attachments = serializers.SerializerMethodField()

    class Meta:
        model = FactoryProfile
        fields = [
            "id",
            "company_name",
            "short_name",
            "region",
            "country",
            "city",
            "intro",
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
            "score",
            "process_names",
            "tags",
            "public_attachments",
        ]
        read_only_fields = fields

    def get_process_names(self, obj):
        lang = self.context.get("lang", "ko")
        from apps.i18n.fields import resolve_i18n

        return [resolve_i18n(p.name, lang) for p in obj.processes.filter(is_active=True)]

    def get_tags(self, obj):
        return [t.tag_name for t in obj.tags.all()]

    def get_public_attachments(self, obj):
        qs = obj.attachments.filter(
            is_public=True, category__in=PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES
        )
        return PublicSupplierAttachmentSerializer(qs, many=True, context=self.context).data


class UserSerializer(serializers.ModelSerializer):
    factory_profile = FactoryProfileSummarySerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "phone",
            "role",
            "member_type",
            "factory_profile",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "role", "member_type", "created_at"]


class MemberRegisterSerializer(serializers.Serializer):
    member_type = serializers.ChoiceField(choices=["individual", "enterprise"], default="individual")
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    company_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    region = serializers.CharField(max_length=120, required=False, allow_blank=True)
    intro = serializers.CharField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    process_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    def validate(self, attrs):
        if attrs.get("member_type") == "enterprise" and not attrs.get("company_name"):
            raise serializers.ValidationError({"company_name": "企业名称必填"})
        return attrs

    def create(self, validated_data):
        member_type = validated_data.pop("member_type", "individual")
        process_ids = validated_data.pop("process_ids", [])
        company_name = validated_data.pop("company_name", "")
        region = validated_data.pop("region", "")
        intro = validated_data.pop("intro", "")
        contact_phone = validated_data.pop("contact_phone", validated_data.get("phone", ""))

        user = User.objects.create_user(
            role="member",
            member_type=member_type,
            is_active=True,
            **validated_data,
        )
        if member_type == "enterprise":
            profile = FactoryProfile.objects.create(
                user=user,
                company_name=company_name,
                region=region,
                intro=intro,
                contact_phone=contact_phone or user.phone,
                status="pending",
            )
            if process_ids:
                profile.processes.set(process_ids)
        return user


class FactoryRegisterSerializer(serializers.Serializer):
    """Deprecated: use MemberRegisterSerializer with member_type=enterprise."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    company_name = serializers.CharField(max_length=200)
    region = serializers.CharField(max_length=120, required=False, allow_blank=True)
    intro = serializers.CharField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    process_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    def create(self, validated_data):
        process_ids = validated_data.pop("process_ids", [])
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data["name"],
            phone=validated_data.get("phone", ""),
            role="member",
            member_type="enterprise",
            is_active=True,
        )
        profile = FactoryProfile.objects.create(
            user=user,
            company_name=validated_data["company_name"],
            region=validated_data.get("region", ""),
            intro=validated_data.get("intro", ""),
            contact_phone=validated_data.get("contact_phone", validated_data.get("phone", "")),
            status="pending",
        )
        if process_ids:
            profile.processes.set(process_ids)
        return user


class FactoryProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    process_ids = serializers.PrimaryKeyRelatedField(
        source="processes", many=True, read_only=True
    )
    tags = SupplierTagSerializer(many=True, read_only=True)
    attachments = SupplierAttachmentSerializer(many=True, read_only=True)
    business_license_url = serializers.SerializerMethodField()

    class Meta:
        model = FactoryProfile
        fields = [
            "id",
            "email",
            "name",
            "company_name",
            "short_name",
            "region",
            "country",
            "city",
            "intro",
            "contact_phone",
            "payment_terms",
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
            "process_ids",
            "tags",
            "attachments",
            "score",
            "is_public",
            "status",
            "business_license_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "name",
            "process_ids",
            "tags",
            "attachments",
            "score",
            "status",
            "business_license_url",
            "created_at",
            "updated_at",
        ]

    def get_business_license_url(self, obj):
        request = self.context.get("request")
        if not obj.business_license:
            return ""
        url = obj.business_license.url
        return request.build_absolute_uri(url) if request else url


class SupplierProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FactoryProfile
        fields = [
            "company_name",
            "short_name",
            "region",
            "country",
            "city",
            "intro",
            "contact_phone",
            "payment_terms",
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
            "is_public",
        ]


class PublicPartnerSerializer(serializers.ModelSerializer):
    process_names = serializers.SerializerMethodField()

    class Meta:
        model = FactoryProfile
        fields = ["id", "company_name", "region", "intro", "process_names", "created_at"]

    def get_process_names(self, obj):
        lang = self.context.get("lang", "ko")
        from apps.i18n.fields import resolve_i18n

        return [
            resolve_i18n(p.name, lang)
            for p in obj.processes.filter(is_active=True)
        ]


class AdminFactorySerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    member_type = serializers.CharField(source="user.member_type", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    process_ids = serializers.SerializerMethodField()
    tags = SupplierTagSerializer(many=True, read_only=True)
    attachments = SupplierAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = FactoryProfile
        fields = [
            "id",
            "user_id",
            "email",
            "name",
            "member_type",
            "company_name",
            "short_name",
            "region",
            "country",
            "city",
            "intro",
            "contact_phone",
            "payment_terms",
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
            "admin_note",
            "score",
            "is_public",
            "process_ids",
            "tags",
            "attachments",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "email",
            "name",
            "member_type",
            "is_active",
            "created_at",
            "updated_at",
            "tags",
            "attachments",
        ]

    def get_process_ids(self, obj):
        return list(obj.processes.values_list("id", flat=True))


class AdminSupplierUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FactoryProfile
        fields = [
            "company_name",
            "short_name",
            "region",
            "country",
            "city",
            "intro",
            "contact_phone",
            "payment_terms",
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
            "admin_note",
            "score",
            "is_public",
            "status",
        ]


class AdminSupplierCreateSerializer(serializers.Serializer):
    """管理员创建供应商账号（不开放供应商自助注册）。"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    company_name = serializers.CharField(max_length=200)
    region = serializers.CharField(max_length=120, required=False, allow_blank=True)
    intro = serializers.CharField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    process_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("邮箱已存在")
        return value

    def create(self, validated_data):
        process_ids = validated_data.pop("process_ids", [])
        company_name = validated_data.pop("company_name")
        region = validated_data.pop("region", "")
        intro = validated_data.pop("intro", "")
        contact_phone = validated_data.pop("contact_phone", "")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data.get("name", ""),
            phone=validated_data.get("phone", ""),
            role="factory",
            member_type="enterprise",
            is_active=True,
        )
        profile = FactoryProfile.objects.create(
            user=user,
            company_name=company_name,
            region=region,
            intro=intro,
            contact_phone=contact_phone or user.phone,
            status="approved",
        )
        if process_ids:
            profile.processes.set(process_ids)
        return user


class AdminMemberSerializer(serializers.ModelSerializer):
    point_balance = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "phone",
            "member_type",
            "is_active",
            "created_at",
            "point_balance",
        ]
        read_only_fields = fields

    def get_point_balance(self, obj):
        from apps.points.services import ensure_wallet

        return ensure_wallet(obj).balance


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "password", "name", "phone", "role", "is_active"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
