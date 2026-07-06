import uuid

from django.db import models


class Contract(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending_sign", "Pending Sign"),
        ("signed", "Signed"),
        ("cancelled", "Cancelled"),
    ]

    contract_no = models.CharField(max_length=32, unique=True, default="")
    rfq = models.ForeignKey(
        "rfq.RFQ", null=True, blank=True, on_delete=models.SET_NULL, related_name="contracts"
    )
    quote = models.ForeignKey(
        "rfq.Quote", null=True, blank=True, on_delete=models.SET_NULL, related_name="contracts"
    )
    production_order = models.OneToOneField(
        "rfq.ProductionOrder", null=True, blank=True, on_delete=models.SET_NULL, related_name="contract"
    )
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="buyer_contracts"
    )
    supplier = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="supplier_contracts"
    )
    title = models.CharField(max_length=200)
    amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="KRW")
    terms = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_sign")
    pdf = models.FileField(upload_to="contract/%Y/%m/", null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_no():
        return f"MC-CT-{uuid.uuid4().hex[:10].upper()}"


class NdaTemplate(models.Model):
    version = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=200, default="保密协议")
    body = models.TextField()
    effective_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]

    def __str__(self):
        return self.version


class NdaSignature(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("signed", "Signed"),
        ("cancelled", "Cancelled"),
    ]

    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="nda_signatures"
    )
    template = models.ForeignKey(NdaTemplate, on_delete=models.PROTECT, related_name="signatures")
    company_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="signed")
    signed_at = models.DateTimeField(null=True, blank=True)
    pdf = models.FileField(upload_to="nda/%Y/%m/", null=True, blank=True)
    retention_delete_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
