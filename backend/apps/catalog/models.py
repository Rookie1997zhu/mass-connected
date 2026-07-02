from django.db import models

from apps.i18n.fields import I18nJSONField


class Category(models.Model):
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    name = I18nJSONField()
    slug = models.SlugField(unique=True, max_length=120)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name_plural = "categories"


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    sku = models.CharField(max_length=64, unique=True)
    name = I18nJSONField()
    description = I18nJSONField(default=dict)
    specs = models.JSONField(default=dict, blank=True)
    price_amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="KRW")
    stock = models.PositiveIntegerField(default=0)
    moq = models.PositiveIntegerField(null=True, blank=True)
    lead_time_days = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_shop_visible = models.BooleanField(default=True)
    is_oem_visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    file = models.ImageField(upload_to="products/%Y/%m/")
    alt_text = I18nJSONField(default=dict, blank=True)
    sort_order = models.IntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]
