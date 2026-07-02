import uuid

from django.db import models

from apps.i18n.fields import I18nJSONField


def generate_rfq_no():
    return f"RFQ{uuid.uuid4().hex[:12].upper()}"


class ServiceCategory(models.Model):
    """制造工艺分类（树形）。仅通过 is_active 下线，不做物理删除。"""

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    name = I18nJSONField()
    slug = models.SlugField(unique=True, max_length=120)
    icon = models.CharField(max_length=64, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]


class RFQ(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("quoting", "Quoting"),
        ("quoted", "Quoted"),
        ("negotiating", "Negotiating"),
        ("won", "Won"),
        ("closed", "Closed"),
    ]
    SCOPE_CHOICES = [
        ("internal", "Internal"),
        ("public", "Public"),
        ("supply_chain", "Supply Chain"),
    ]

    rfq_no = models.CharField(max_length=32, unique=True, default=generate_rfq_no)
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="rfqs"
    )
    contact_name = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    company = models.CharField(max_length=200, blank=True)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default="internal")
    service_category = models.ForeignKey(
        ServiceCategory, on_delete=models.PROTECT, related_name="rfqs"
    )
    material = models.CharField(max_length=200, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    tolerance = models.CharField(max_length=200, blank=True)
    surface_finish = models.CharField(max_length=200, blank=True)
    target_delivery_date = models.DateField(null=True, blank=True)
    budget_amount = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="KRW")
    remark = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class RFQAttachment(models.Model):
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="rfq/%Y/%m/")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=32, blank=True)
    size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class Quote(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="quotes")
    supplier = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="quotes"
    )
    price_amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="KRW")
    lead_time_days = models.PositiveIntegerField(default=0)
    valid_until = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_quotes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
