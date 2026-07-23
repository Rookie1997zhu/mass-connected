from rest_framework import serializers

from apps.chat.models import ChatAttachment, Conversation, Message


class ChatAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatAttachment
        fields = ["id", "file_name", "file_type", "size", "uploaded_at"]


class MessageSerializer(serializers.ModelSerializer):
    attachments = ChatAttachmentSerializer(many=True, read_only=True)
    body_original = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation_id",
            "sender_id",
            "sender_role",
            "body",
            "body_original",
            "has_contact_hint",
            "created_at",
            "attachments",
        ]

    def get_body_original(self, obj):
        if self.context.get("include_original"):
            return obj.body_original
        return None


class ConversationSerializer(serializers.ModelSerializer):
    peer_display_name = serializers.SerializerMethodField()
    quote_request_no = serializers.CharField(source="quote_request.request_no", read_only=True)
    unread = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "quote_request_id",
            "quote_request_no",
            "buyer_id",
            "supplier_id",
            "production_order_id",
            "project_id",
            "dispute_status",
            "dispute_reason",
            "disputed_at",
            "last_message_at",
            "created_at",
            "peer_display_name",
            "unread",
            "last_message_preview",
        ]

    def get_peer_display_name(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None

        def _name(peer):
            profile = getattr(peer, "factory_profile", None)
            if profile and getattr(profile, "company_name", None):
                return profile.company_name
            return getattr(peer, "email", "") or f"User#{peer.id}"

        if user and user.id == obj.buyer_id:
            return _name(obj.supplier)
        if user and user.id == obj.supplier_id:
            return _name(obj.buyer)
        return f"{_name(obj.buyer)} / {_name(obj.supplier)}"

    def get_unread(self, obj):
        from django.core.cache import cache

        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if not user:
            return 0
        return int(cache.get(f"chat:unread_conv:{user.id}:{obj.id}") or 0)

    def get_last_message_preview(self, obj):
        last = obj.messages.order_by("-id").first()
        if not last:
            return ""
        return (last.body or "")[:120]


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=4000, allow_blank=False)


class DisputeOpenSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ConversationCreateSerializer(serializers.Serializer):
    quote_request_id = serializers.IntegerField()
