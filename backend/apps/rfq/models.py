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
        ("pending_review", "Pending Review"),
        ("assigned", "Assigned"),
        ("quoting", "Quoting"),
        ("quoted", "Quoted"),
        ("comparing", "Comparing"),
        ("customer_confirming", "Customer Confirming"),
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
    markup_percent = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["buyer", "-created_at"], name="rfq_buyer_created_idx"),
            models.Index(fields=["status", "scope", "-created_at"], name="rfq_status_scope_idx"),
        ]


class RFQAttachment(models.Model):
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="rfq/%Y/%m/")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=32, blank=True)
    size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


def generate_quote_request_no():
    return f"QR{uuid.uuid4().hex[:12].upper()}"


class QuoteRequest(models.Model):
    """管理员把 RFQ 指派给指定供应商的报价请求。供应商只能看到被指派的项目。"""

    STATUS_CHOICES = [
        ("assigned", "Assigned"),
        ("viewed", "Viewed"),
        ("quoted", "Quoted"),
        ("needs_revision", "Needs Revision"),
        ("adopted", "Adopted"),
        ("not_adopted", "Not Adopted"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    ]

    request_no = models.CharField(max_length=32, unique=True, default=generate_quote_request_no)
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="quote_requests")
    supplier = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="quote_requests"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="assigned")
    deadline = models.DateField(null=True, blank=True)
    admin_note = models.TextField(blank=True)
    is_urgent = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_quote_requests"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("rfq", "supplier")]
        indexes = [
            models.Index(fields=["supplier", "status", "-created_at"], name="qr_supplier_status_idx"),
            models.Index(fields=["rfq", "status"], name="qr_rfq_status_idx"),
        ]


class Quote(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="quotes")
    quote_request = models.ForeignKey(
        QuoteRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="quotes"
    )
    supplier = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="quotes"
    )
    price_amount = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField(null=True, blank=True)
    mold_fee = models.PositiveIntegerField(null=True, blank=True)
    sample_fee = models.PositiveIntegerField(null=True, blank=True)
    moq = models.PositiveIntegerField(null=True, blank=True)
    payment_terms = models.CharField(max_length=200, blank=True)
    currency = models.CharField(max_length=3, default="KRW")
    lead_time_days = models.PositiveIntegerField(default=0)
    valid_until = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    is_customer_visible = models.BooleanField(default=False)
    plan_label = models.CharField(max_length=8, blank=True)
    revision_version = models.PositiveIntegerField(default=1)
    revised_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_quotes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class QuoteAttachment(models.Model):
    """供应商为某份报价上传的报价资料附件。"""

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="quote/%Y/%m/")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=32, blank=True)
    size = models.PositiveIntegerField(default=0)
    uploader = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="quote_attachments"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "id"]

    def __str__(self):
        return self.file_name


def generate_production_order_no():
    return f"PO{uuid.uuid4().hex[:12].upper()}"


class ProductionOrder(models.Model):
    STATUS_CHOICES = [
        ("pending_confirm", "Pending Confirm"),
        ("confirmed", "Confirmed"),
        ("in_production", "In Production"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    order_no = models.CharField(max_length=32, unique=True, default=generate_production_order_no)
    rfq = models.ForeignKey(RFQ, on_delete=models.PROTECT, related_name="production_orders")
    quote = models.OneToOneField(Quote, on_delete=models.PROTECT, related_name="production_order")
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="buyer_production_orders"
    )
    supplier = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="supplier_production_orders"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_confirm")
    # price_amount 兼容旧字段，语义等同客户价（加价后）
    price_amount = models.PositiveIntegerField()
    supplier_amount = models.PositiveIntegerField(null=True, blank=True)
    customer_amount = models.PositiveIntegerField(null=True, blank=True)
    markup_percent_snapshot = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="KRW")
    lead_time_days = models.PositiveIntegerField(default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def display_customer_amount(self):
        if self.customer_amount is not None:
            return self.customer_amount
        return self.price_amount

    def display_supplier_amount(self):
        if self.supplier_amount is not None:
            return self.supplier_amount
        return self.price_amount

    class Meta:
        ordering = ["-created_at"]
