from django.db import models


class Notification(models.Model):
    TYPE_CHOICES = [
        ("quote", "Quote"),
        ("project", "Project"),
        ("payment", "Payment"),
        ("contract", "Contract"),
        ("production_order", "Production Order"),
        ("quote_request", "Quote Request"),
            ("point", "Point"),
            ("system", "System"),
            ("chat", "Chat"),
        ]

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, default="system")
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    related_type = models.CharField(max_length=64, blank=True)
    related_id = models.PositiveIntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
