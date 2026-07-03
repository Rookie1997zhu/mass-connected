import apps.rfq.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_member_type_migrate_factory"),
        ("rfq", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductionOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "order_no",
                    models.CharField(
                        default=apps.rfq.models.generate_production_order_no,
                        max_length=32,
                        unique=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending_confirm", "Pending Confirm"),
                            ("confirmed", "Confirmed"),
                            ("in_production", "In Production"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending_confirm",
                        max_length=20,
                    ),
                ),
                ("price_amount", models.PositiveIntegerField()),
                ("currency", models.CharField(default="KRW", max_length=3)),
                ("lead_time_days", models.PositiveIntegerField(default=0)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "buyer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="buyer_production_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "quote",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="production_order",
                        to="rfq.quote",
                    ),
                ),
                (
                    "rfq",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="production_orders",
                        to="rfq.rfq",
                    ),
                ),
                (
                    "supplier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_production_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
