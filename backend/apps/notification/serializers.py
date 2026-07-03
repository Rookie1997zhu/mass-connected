from rest_framework import serializers

from apps.notification.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "content",
            "related_type",
            "related_id",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields
