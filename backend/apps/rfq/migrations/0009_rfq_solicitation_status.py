from django.db import migrations, models


OPEN_LEGACY = {"submitted", "quoting", "quoted", "negotiating", "comparing", "customer_confirming"}


def backfill_solicitation(apps, schema_editor):
    RFQ = apps.get_model("rfq", "RFQ")
    for rfq in RFQ.objects.all().iterator():
        if rfq.scope == "public" and rfq.status in OPEN_LEGACY:
            rfq.solicitation_status = "open"
        else:
            rfq.solicitation_status = "closed"
        rfq.save(update_fields=["solicitation_status"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("rfq", "0008_qr_list_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="rfq",
            name="solicitation_status",
            field=models.CharField(
                choices=[("open", "Open"), ("paused", "Paused"), ("closed", "Closed")],
                db_index=True,
                default="closed",
                max_length=16,
            ),
        ),
        migrations.AddIndex(
            model_name="rfq",
            index=models.Index(
                fields=["scope", "solicitation_status", "-created_at"],
                name="rfq_scope_solicitation_idx",
            ),
        ),
        migrations.RunPython(backfill_solicitation, noop_reverse),
    ]
