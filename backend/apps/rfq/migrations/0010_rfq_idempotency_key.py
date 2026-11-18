from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rfq", "0009_rfq_solicitation_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="rfq",
            name="idempotency_key",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddConstraint(
            model_name="rfq",
            constraint=models.UniqueConstraint(
                condition=~models.Q(idempotency_key=""),
                fields=("buyer", "idempotency_key"),
                name="rfq_buyer_idempotency_uniq",
            ),
        ),
    ]
