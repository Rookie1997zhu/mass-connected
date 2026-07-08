from decimal import Decimal

from django.db import migrations, models


def seed_dieline_templates(apps, schema_editor):
    DielineTemplate = apps.get_model("simplequote", "DielineTemplate")
    seeds = [
        {
            "code": "0201",
            "category_code": "0200",
            "engine_key": "slotted_rsc",
            "default_length_mm": Decimal("434"),
            "default_width_mm": Decimal("214"),
            "default_height_mm": Decimal("278"),
            "default_thickness_mm": Decimal("3"),
            "sort_order": 1,
        },
        {
            "code": "0427",
            "category_code": "0400",
            "engine_key": "mailer_folder",
            "default_length_mm": Decimal("315"),
            "default_width_mm": Decimal("202"),
            "default_height_mm": Decimal("62"),
            "default_thickness_mm": Decimal("1.5"),
            "sort_order": 2,
        },
        {
            "code": "0713",
            "category_code": "0700",
            "engine_key": "tuck_end",
            "default_length_mm": Decimal("200"),
            "default_width_mm": Decimal("150"),
            "default_height_mm": Decimal("100"),
            "default_thickness_mm": Decimal("1.5"),
            "sort_order": 3,
        },
        {
            "code": "0716",
            "category_code": "0700",
            "engine_key": "auto_lock_bottom",
            "default_length_mm": Decimal("200"),
            "default_width_mm": Decimal("150"),
            "default_height_mm": Decimal("100"),
            "default_thickness_mm": Decimal("1.5"),
            "sort_order": 4,
        },
    ]
    for item in seeds:
        DielineTemplate.objects.update_or_create(
            code=item["code"],
            defaults={
                "category_code": item["category_code"],
                "engine_key": item["engine_key"],
                "name_i18n": {},
                "desc_i18n": {},
                "default_length_mm": item["default_length_mm"],
                "default_width_mm": item["default_width_mm"],
                "default_height_mm": item["default_height_mm"],
                "default_thickness_mm": item["default_thickness_mm"],
                "default_glue_tab_mm": Decimal("25"),
                "allowances": {},
                "priority": "P0",
                "quote_enabled": True,
                "preview_enabled": True,
                "sort_order": item["sort_order"],
                "is_active": True,
            },
        )


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
