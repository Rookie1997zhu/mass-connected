from rest_framework import serializers

from apps.accounts.models import FactoryProfile, User


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
            "established_year",
            "employee_scale",
            "factory_area_sqm",
            "main_products",
            "monthly_capacity",
            "quality_certifications",
            "equipment_summary",
        ]


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
            is_verified=False,
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
