from rest_framework import serializers

from apps.accounts.models import FactoryProfile, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "phone", "role", "is_active", "created_at"]
        read_only_fields = ["id", "role", "created_at"]


class MemberRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password", "name", "phone"]

    def create(self, validated_data):
        return User.objects.create_user(role="member", **validated_data)


class FactoryRegisterSerializer(serializers.Serializer):
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
            role="factory",
            is_active=False,
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

    class Meta:
        model = FactoryProfile
        fields = [
            "id",
            "email",
            "name",
            "company_name",
            "region",
            "intro",
            "contact_phone",
            "process_ids",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class AdminFactorySerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    process_ids = serializers.SerializerMethodField()

    class Meta:
        model = FactoryProfile
        fields = [
            "id",
            "email",
            "name",
            "company_name",
            "region",
            "intro",
            "contact_phone",
            "process_ids",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "email", "name", "is_active", "created_at", "updated_at"]

    def get_process_ids(self, obj):
        return list(obj.processes.values_list("id", flat=True))


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "password", "name", "phone", "role", "is_active"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
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
