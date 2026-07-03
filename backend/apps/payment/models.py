import uuid

from django.db import models


class Payment(models.Model):
    STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("pending_confirm", "Pending Confirm"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]

    payment_no = models.CharField(max_length=32, unique=True, default="")
    contract = models.ForeignKey(
        "contract.Contract", null=True, blank=True, on_delete=models.SET_NULL, related_name="payments"
    )
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="KRW")
    method = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unpaid")
    proof = models.FileField(upload_to="payment/%Y/%m/", null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    confirmed_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="confirmed_payments"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_no():
        return f"MC-PAY-{uuid.uuid4().hex[:10].upper()}"
