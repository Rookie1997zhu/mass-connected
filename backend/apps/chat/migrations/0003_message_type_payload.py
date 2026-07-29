from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0002_chat_indexes_and_notif_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="message_type",
            field=models.CharField(
                choices=[("text", "Text"), ("order_card", "Order Card")],
                db_index=True,
                default="text",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="payload",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
