from django.contrib import admin

from apps.chat.models import ChatAttachment, Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "quote_request",
        "buyer",
        "supplier",
        "dispute_status",
        "last_message_at",
    )
    list_filter = ("dispute_status",)
    search_fields = ("quote_request__request_no",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender_role", "has_contact_hint", "created_at")
    list_filter = ("sender_role", "has_contact_hint")


@admin.register(ChatAttachment)
class ChatAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "file_name", "size", "uploaded_at")
