"""刀版精度升级：楞型/工艺参数/生产参考资产。"""

from decimal import Decimal

from django.db import migrations, models


def backfill_precision_defaults(apps, schema_editor):
    pass


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("simplequote", "0005_dieline_category_and_dimensions"),
    ]

    operations = [
        migrations.AddField(
            model_name="dielinetemplate",
            name="flute_type",
            field=models.CharField(
                choices=[
                    ("e", "E flute"),
                    ("b", "B flute"),
                    ("c", "C flute"),
                    ("bc", "BC flute"),
                    ("none", "Non-flute"),
                ],
                default="b",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="material_type",
            field=models.CharField(
                choices=[
                    ("corrugated", "Corrugated"),
                    ("white_card", "White card"),
                    ("kraft", "Kraft"),
                    ("coated", "Coated"),
                ],
                default="corrugated",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="default_dimension_type",
            field=models.CharField(
                choices=[
                    ("internal", "Internal"),
                    ("external", "External"),
                    ("manufacturing", "Manufacturing"),
                ],
                default="internal",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="min_length_mm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="max_length_mm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="min_width_mm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="max_width_mm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="min_height_mm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="max_height_mm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="slot_gap_mm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="crease_gap_mm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="flap_gap_mm",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="structure_params",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="production_asset",
            field=models.FileField(blank=True, null=True, upload_to="dieline_production/%Y/%m/"),
        ),
        migrations.RunPython(backfill_precision_defaults, reverse_backfill),
    ]
