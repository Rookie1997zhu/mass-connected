import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("rfq", "0006_quote_detail_attachments_and_supplier_profile"),
        ("project", "0003_detailed_quote_fulfillment_upgrade"),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "dispute_status",
                    models.CharField(
                        choices=[("none", "None"), ("open", "Open"), ("resolved", "Resolved")],
                        db_index=True,
                        default="none",
                        max_length=16,
                    ),
                ),
                ("disputed_at", models.DateTimeField(blank=True, null=True)),
                ("dispute_reason", models.TextField(blank=True)),
                ("last_message_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "buyer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="buyer_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "disputed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="opened_chat_disputes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "production_order",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="conversations",
                        to="rfq.productionorder",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="conversations",
                        to="project.project",
                    ),
                ),
                (
                    "quote_request",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversation",
                        to="rfq.quoterequest",
                    ),
                ),
                (
                    "supplier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-last_message_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "sender_role",
                    models.CharField(
                        choices=[
                            ("buyer", "Buyer"),
                            ("supplier", "Supplier"),
                            ("platform", "Platform"),
                        ],
                        max_length=16,
                    ),
                ),
                ("body", models.TextField()),
                ("body_original", models.TextField(blank=True)),
                ("has_contact_hint", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="chat.conversation",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="chat_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="ChatAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="chat/%Y/%m/")),
                ("file_name", models.CharField(max_length=255)),
                ("file_type", models.CharField(blank=True, max_length=64)),
                ("size", models.PositiveIntegerField(default=0)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="chat.message",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(fields=["buyer", "last_message_at"], name="chat_conver_buyer_i_0a1b2c_idx"),
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(fields=["supplier", "last_message_at"], name="chat_conver_supplie_1d2e3f_idx"),
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["dispute_status", "last_message_at"],
                name="chat_conver_dispute_2e3f4a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["conversation", "id"], name="chat_messag_convers_3f4a5b_idx"),
        ),
    ]
