import uuid

from django.db import models
from django.utils import timezone


FEATURE_SIMPLE_QUOTE = "simple_quote"
KNOWN_FEATURE_CODES = (FEATURE_SIMPLE_QUOTE,)


class PlanVersion(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    ]
    PERIOD_MONTH = "month"
    PERIOD_YEAR = "year"
    PERIOD_NONE = "none"
    PERIOD_CHOICES = [
        (PERIOD_MONTH, "Month"),
        (PERIOD_YEAR, "Year"),
        (PERIOD_NONE, "None"),
    ]

    code = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    billing_period = models.CharField(max_length=16, choices=PERIOD_CHOICES, default=PERIOD_MONTH)
    price_amount = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="KRW", blank=True)
    # feature_code -> period limit (int). 0 or missing = not included.
    features_json = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["code", "status"], name="plan_code_status_idx"),
        ]

    def __str__(self):
        return f"{self.code}#{self.pk} ({self.status})"

    @property
    def is_orderable(self):
        return (
            self.status == self.STATUS_PUBLISHED
            and self.price_amount is not None
            and int(self.price_amount) > 0
        )


class Subscription(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    ]
    SOURCE_ADMIN_GRANT = "admin_grant"
    SOURCE_ORDER = "order"
    SOURCE_CHOICES = [
        (SOURCE_ADMIN_GRANT, "Admin Grant"),
        (SOURCE_ORDER, "Order"),
    ]

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan_version = models.ForeignKey(
        PlanVersion, on_delete=models.PROTECT, related_name="subscriptions"
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default=SOURCE_ADMIN_GRANT)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    granted_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="granted_subscriptions",
    )
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "status", "-ends_at"], name="sub_user_status_ends_idx"),
        ]

    def __str__(self):
        return f"Sub#{self.pk} user={self.user_id} {self.status}"

    def is_currently_active(self, now=None):
        now = now or timezone.now()
        if self.status != self.STATUS_ACTIVE:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at <= now:
            return False
        return True


class FeatureEntitlement(models.Model):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="feature_entitlements"
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="entitlements"
    )
    feature_code = models.CharField(max_length=64, db_index=True)
    period_limit = models.PositiveIntegerField(default=0)
    period_used = models.PositiveIntegerField(default=0)
    period_reserved = models.PositiveIntegerField(default=0)
    period_reset_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["feature_code", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "feature_code"],
                name="uniq_entitlement_sub_feature",
            )
        ]

    @property
    def remaining(self):
        used = int(self.period_used or 0) + int(self.period_reserved or 0)
        return max(0, int(self.period_limit or 0) - used)


class UsageLedger(models.Model):
    ACTION_RESERVE = "reserve"
    ACTION_COMMIT = "commit"
    ACTION_RELEASE = "release"
    ACTION_CHOICES = [
        (ACTION_RESERVE, "Reserve"),
        (ACTION_COMMIT, "Commit"),
        (ACTION_RELEASE, "Release"),
    ]
    STATUS_RESERVED = "reserved"
    STATUS_COMMITTED = "committed"
    STATUS_RELEASED = "released"
    STATUS_CHOICES = [
        (STATUS_RESERVED, "Reserved"),
        (STATUS_COMMITTED, "Committed"),
        (STATUS_RELEASED, "Released"),
    ]

    ledger_no = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="usage_ledgers"
    )
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="usage_ledgers",
    )
    feature_code = models.CharField(max_length=64, db_index=True)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_RESERVED)
    idempotency_key = models.CharField(max_length=64, unique=True)
    source_type = models.CharField(max_length=64, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "feature_code", "-created_at"], name="ledger_user_feat_idx"),
        ]

    @staticmethod
    def generate_no():
        return f"UL{uuid.uuid4().hex[:14].upper()}"


class SubscriptionOrder(models.Model):
    STATUS_PENDING = "pending_confirm"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Confirm"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    order_no = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="subscription_orders"
    )
    plan_version = models.ForeignKey(
        PlanVersion, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    price_amount = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="KRW", blank=True)
    proof = models.FileField(upload_to="subscription_orders/%Y/%m/", null=True, blank=True)
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    confirmed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_subscription_orders",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @staticmethod
    def generate_no():
        return f"SO{uuid.uuid4().hex[:14].upper()}"
