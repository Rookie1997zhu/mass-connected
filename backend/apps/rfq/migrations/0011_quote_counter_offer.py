# Generated manually for S3 QuoteCounterOffer

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("rfq", "0010_rfq_idempotency_key"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuoteCounterOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(blank=True, null=True)),
                ("target_total_amount", models.PositiveIntegerField()),
                ("currency", models.CharField(default="KRW", max_length=3)),
                ("lead_time_days", models.PositiveIntegerField(blank=True, null=True)),
                ("note", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                            ("withdrawn", "Withdrawn"),
                            ("expired", "Expired"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_counter_offers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "quote",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="counter_offers",
                        to="rfq.quote",
                    ),
                ),
                (
                    "rfq",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="counter_offers",
                        to="rfq.rfq",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="quotecounteroffer",
            index=models.Index(fields=["quote", "status", "-created_at"], name="qco_quote_status_idx"),
        ),
        migrations.AddIndex(
            model_name="quotecounteroffer",
            index=models.Index(fields=["rfq", "status", "-created_at"], name="qco_rfq_status_idx"),
        ),
    ]
