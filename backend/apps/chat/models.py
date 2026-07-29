from django.conf import settings
from django.db import models


class Conversation(models.Model):
    DISPUTE_NONE = "none"
    DISPUTE_OPEN = "open"
    DISPUTE_RESOLVED = "resolved"
    DISPUTE_STATUS_CHOICES = [
        (DISPUTE_NONE, "None"),
        (DISPUTE_OPEN, "Open"),
        (DISPUTE_RESOLVED, "Resolved"),
    ]

    quote_request = models.OneToOneField(
        "rfq.QuoteRequest",
        on_delete=models.CASCADE,
        related_name="conversation",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="buyer_conversations",
    )
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supplier_conversations",
    )
    production_order = models.ForeignKey(
        "rfq.ProductionOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations",
    )
    project = models.ForeignKey(
        "project.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations",
    )
    dispute_status = models.CharField(
        max_length=16, choices=DISPUTE_STATUS_CHOICES, default=DISPUTE_NONE, db_index=True
    )
    disputed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="opened_chat_disputes",
    )
    disputed_at = models.DateTimeField(null=True, blank=True)
    dispute_reason = models.TextField(blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_message_at", "-id"]
        indexes = [
            models.Index(fields=["buyer", "last_message_at"]),
            models.Index(fields=["supplier", "last_message_at"]),
            models.Index(fields=["dispute_status", "last_message_at"]),
        ]

    def __str__(self):
        return f"Conversation#{self.pk} QR#{self.quote_request_id}"


class Message(models.Model):
    ROLE_BUYER = "buyer"
    ROLE_SUPPLIER = "supplier"
    ROLE_PLATFORM = "platform"
    SENDER_ROLE_CHOICES = [
        (ROLE_BUYER, "Buyer"),
        (ROLE_SUPPLIER, "Supplier"),
        (ROLE_PLATFORM, "Platform"),
    ]

    TYPE_TEXT = "text"
    TYPE_ORDER_CARD = "order_card"
    MESSAGE_TYPE_CHOICES = [
        (TYPE_TEXT, "Text"),
        (TYPE_ORDER_CARD, "Order Card"),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chat_messages",
    )
    sender_role = models.CharField(max_length=16, choices=SENDER_ROLE_CHOICES)
    message_type = models.CharField(
        max_length=32, choices=MESSAGE_TYPE_CHOICES, default=TYPE_TEXT, db_index=True
    )
    payload = models.JSONField(null=True, blank=True)
    body = models.TextField()
    body_original = models.TextField(blank=True)
    has_contact_hint = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["conversation", "id"]),
        ]

    def __str__(self):
        return f"Message#{self.pk}"


class ChatAttachment(models.Model):
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="chat/%Y/%m/")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=64, blank=True)
    size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.file_name
