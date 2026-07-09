from django.db import migrations


def remove_templates_without_assets(apps, schema_editor):
    DielineTemplate = apps.get_model("simplequote", "DielineTemplate")
    DielineTemplate.objects.filter(assets__isnull=True).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("simplequote", "0007_dieline_template_asset"),
    ]

    operations = [
        migrations.RunPython(remove_templates_without_assets, noop_reverse),
    ]
