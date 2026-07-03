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
