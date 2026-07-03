from django.db import migrations, models


def migrate_member_types(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="member", member_type__isnull=True).update(member_type="individual")
    User.objects.filter(role="factory").update(role="member", member_type="enterprise", is_active=True)


def reverse_member_types(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(member_type="enterprise").update(role="factory")
    User.objects.filter(member_type="individual").update(member_type=None)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_user_role_factoryprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="member_type",
            field=models.CharField(
                blank=True,
                choices=[("individual", "Individual"), ("enterprise", "Enterprise")],
                max_length=20,
                null=True,
            ),
        ),
        migrations.RunPython(migrate_member_types, reverse_member_types),
    ]
