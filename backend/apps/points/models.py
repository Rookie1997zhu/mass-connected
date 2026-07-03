import uuid

from django.db import models


class PointWallet(models.Model):
    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="point_wallet"
    )
    balance = models.PositiveIntegerField(default=0)
    frozen_balance = models.PositiveIntegerField(default=0)
    total_earned = models.PositiveIntegerField(default=0)
    total_spent = models.PositiveIntegerField(default=0)
    total_recharged = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PointTransaction(models.Model):
    TYPE_CHOICES = [
        ("earn", "Earn"),
        ("spend", "Spend"),
        ("recharge", "Recharge"),
        ("refund", "Refund"),
        ("adjust", "Adjust"),
        ("expire", "Expire"),
    ]

    transaction_no = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="point_transactions"
    )
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    amount = models.IntegerField()
    balance_before = models.PositiveIntegerField(default=0)
    balance_after = models.PositiveIntegerField(default=0)
    source_type = models.CharField(max_length=64, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    admin = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="point_admin_ops"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_no():
        return f"PT{uuid.uuid4().hex[:14].upper()}"


class PointRule(models.Model):
    RULE_TYPE_CHOICES = [
        ("earn", "Earn"),
        ("spend", "Spend"),
        ("recharge", "Recharge"),
    ]

    rule_code = models.CharField(max_length=64, unique=True)
    rule_name = models.CharField(max_length=120)
    rule_type = models.CharField(max_length=16, choices=RULE_TYPE_CHOICES, default="spend")
    point_amount = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rule_code"]


class RechargeOrder(models.Model):
    STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("pending_confirm", "Pending Confirm"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]

    recharge_no = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="recharge_orders"
    )
    amount_krw = models.PositiveIntegerField()
    vat_amount = models.PositiveIntegerField(default=0)
    total_pay_amount = models.PositiveIntegerField(default=0)
    point_amount = models.PositiveIntegerField(default=0)
    payment_method = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_confirm")
    proof = models.FileField(upload_to="recharge/%Y/%m/", null=True, blank=True)
    confirmed_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="confirmed_recharges"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_no():
        return f"RC{uuid.uuid4().hex[:12].upper()}"
