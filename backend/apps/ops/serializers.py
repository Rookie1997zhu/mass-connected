from rest_framework import serializers


class OpsStorageQuerySerializer(serializers.Serializer):
    recount = serializers.BooleanField(required=False, default=False)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)


class OpsBehaviorQuerySerializer(serializers.Serializer):
    days = serializers.IntegerField(required=False, default=7)

    def validate_days(self, value):
        if value not in (7, 30):
            raise serializers.ValidationError("天数只能是 7 或 30")
        return value
