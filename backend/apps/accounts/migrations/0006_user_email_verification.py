from django.db import migrations, models
from django.utils import timezone


def mark_existing_users_verified(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_verified=False).update(
        is_verified=True,
        email_verified_at=timezone.now(),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_quote_detail_attachments_and_supplier_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="is_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_existing_users_verified, migrations.RunPython.noop),
    ]
