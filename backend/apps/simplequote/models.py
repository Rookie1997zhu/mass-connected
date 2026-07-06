import uuid

from django.db import models


class QuoteTable(models.Model):
    """简单报价多列表格（费率阶梯、计分表、定价行等），后台可维护。"""

    quote_type = models.CharField(max_length=32)
    table_key = models.CharField(max_length=64)
    rows = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["quote_type", "table_key"]
        unique_together = [("quote_type", "table_key")]


class QuoteParam(models.Model):
    """简单报价参数（材料单价、机时费率、模具等级价等），后台可维护。"""

    quote_type = models.CharField(max_length=32)
    param_key = models.CharField(max_length=64)
    label = models.CharField(max_length=120, blank=True)
    value = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    unit = models.CharField(max_length=32, blank=True)
    note = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["quote_type", "param_key"]
        unique_together = [("quote_type", "param_key")]


class SimpleQuote(models.Model):
    TYPE_CHOICES = [
        ("injection", "Injection Mold"),
        ("print3d", "3D Printing"),
        ("pcba", "PCBA Assembly"),
        ("pcb", "PCB Development"),
        ("software", "Software"),
        ("ic", "IC Design"),
        ("paper_box", "Paper Box"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("calculated", "Calculated"),
        ("pdf_generated", "PDF Generated"),
        ("converted", "Converted to Detail"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    quote_no = models.CharField(max_length=32, unique=True)
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="simple_quotes"
    )
    quote_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    product_name = models.CharField(max_length=200, blank=True)
    inputs = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    total_amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="KRW")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="calculated")
    valid_until = models.DateField(null=True, blank=True)
    points_spent = models.PositiveIntegerField(default=0)
    pdf = models.FileField(upload_to="simple_quote/%Y/%m/", null=True, blank=True)
    converted_rfq = models.ForeignKey(
        "rfq.RFQ", null=True, blank=True, on_delete=models.SET_NULL, related_name="from_simple_quotes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_no():
        return f"MC-QT-{uuid.uuid4().hex[:10].upper()}"
