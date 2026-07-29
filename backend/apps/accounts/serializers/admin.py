from rest_framework import serializers

from apps.accounts.models import FactoryProfile, User
from apps.accounts.serializers.base import (
    SupplierAttachmentSerializer,
    SupplierTagSerializer,
)


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
