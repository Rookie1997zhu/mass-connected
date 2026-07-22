from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contract", "0003_detailed_quote_fulfillment_upgrade"),
    ]

    operations = [
        migrations.AddField(
            model_name="contract",
            name="agree_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contract",
            name="business_reg_no",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="contract",
            name="company_address",
            field=models.CharField(blank=True, default="", max_length=300),
        ),
        migrations.AddField(
            model_name="contract",
            name="company_name",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="contract",
            name="signature_image",
            field=models.ImageField(
                blank=True, null=True, upload_to="contract/signatures/%Y/%m/"
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="signer_name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AlterField(
            model_name="contracttemplate",
            name="body",
            field=models.TextField(
                help_text="支持占位符：{{contract_no}} {{rfq_no}} {{order_no}} {{buyer_name}} "
                "{{supplier_name}} {{company_name}} {{business_reg_no}} {{company_address}} "
                "{{signer_name}} {{amount}} {{currency}} {{lead_time_days}} {{payment_terms}} {{date}}"
            ),
        ),
    ]
