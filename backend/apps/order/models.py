import uuid

from django.db import models


def generate_order_no():
    return f"ORD{uuid.uuid4().hex[:12].upper()}"


class CartItem(models.Model):
    member = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price_amount = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("member", "product")
        ordering = ["-updated_at"]


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("awaiting_payment", "Awaiting Payment"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]

    order_no = models.CharField(max_length=32, unique=True, default=generate_order_no)
    member = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="KRW")
    shipping_name = models.CharField(max_length=120)
    shipping_phone = models.CharField(max_length=32)
    shipping_address = models.TextField()
    remark = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="order_items")
    product_name = models.JSONField(default=dict)
    quantity = models.PositiveIntegerField()
    unit_price_amount = models.PositiveIntegerField()
    line_total_amount = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]
