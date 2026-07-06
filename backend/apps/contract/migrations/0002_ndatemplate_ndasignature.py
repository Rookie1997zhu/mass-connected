from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_user_role_factoryprofile"),
        ("contract", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NdaTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.CharField(max_length=32, unique=True)),
                ("title", models.CharField(default="保密协议", max_length=200)),
                ("body", models.TextField()),
                ("effective_date", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-effective_date", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="NdaSignature",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_name", models.CharField(max_length=200)),
                ("status", models.CharField(
                    choices=[("pending", "Pending"), ("signed", "Signed"), ("cancelled", "Cancelled")],
                    default="signed",
                    max_length=20,
                )),
                ("signed_at", models.DateTimeField(blank=True, null=True)),
                ("pdf", models.FileField(blank=True, null=True, upload_to="nda/%Y/%m/")),
                ("retention_delete_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("buyer", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="nda_signatures",
                    to="accounts.user",
                )),
                ("template", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="signatures",
                    to="contract.ndatemplate",
                )),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
