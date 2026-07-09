from decimal import Decimal

from django.db import migrations, models


def seed_dieline_templates(apps, schema_editor):
    pass


def unseed_dieline_templates(apps, schema_editor):
    DielineTemplate = apps.get_model("simplequote", "DielineTemplate")
    DielineTemplate.objects.filter(code__in=["0201", "0427", "0713", "0716"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("simplequote", "0002_quotetable"),
    ]

    operations = [
        migrations.CreateModel(
            name="DielineTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=16, unique=True)),
                ("category_code", models.CharField(max_length=16)),
                (
                    "engine_key",
                    models.CharField(
                        choices=[
                            ("slotted_rsc", "Slotted RSC"),
                            ("mailer_folder", "Mailer folder"),
                            ("tuck_end", "Tuck end"),
                            ("auto_lock_bottom", "Auto lock bottom"),
                        ],
                        max_length=32,
                    ),
                ),
                ("name_i18n", models.JSONField(blank=True, default=dict)),
                ("desc_i18n", models.JSONField(blank=True, default=dict)),
                ("default_length_mm", models.DecimalField(decimal_places=2, default=200, max_digits=10)),
                ("default_width_mm", models.DecimalField(decimal_places=2, default=150, max_digits=10)),
                ("default_height_mm", models.DecimalField(decimal_places=2, default=100, max_digits=10)),
                ("default_thickness_mm", models.DecimalField(decimal_places=2, default=1.5, max_digits=8)),
                ("default_glue_tab_mm", models.DecimalField(decimal_places=2, default=25, max_digits=8)),
                ("allowances", models.JSONField(blank=True, default=dict)),
                (
                    "priority",
                    models.CharField(choices=[("P0", "P0"), ("P1", "P1")], default="P0", max_length=8),
                ),
                ("quote_enabled", models.BooleanField(default=True)),
                ("preview_enabled", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("thumbnail", models.ImageField(blank=True, null=True, upload_to="dieline_template/%Y/%m/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "code"],
            },
        ),
        migrations.RunPython(seed_dieline_templates, unseed_dieline_templates),
    ]
