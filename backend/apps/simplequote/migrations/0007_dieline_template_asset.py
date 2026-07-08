from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("simplequote", "0006_dieline_precision_upgrade"),
    ]

    operations = [
        migrations.CreateModel(
            name="DielineTemplateAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_file", models.FileField(upload_to="dieline_assets/%Y/%m/")),
                (
                    "source_format",
                    models.CharField(
                        choices=[("dxf", "DXF"), ("svg", "SVG"), ("ai", "AI"), ("pdf", "PDF")],
                        max_length=8,
                    ),
                ),
                ("parsed_geometry", models.JSONField(blank=True, default=dict)),
                ("mapping_schema", models.JSONField(blank=True, default=dict)),
                ("base_dimensions", models.JSONField(blank=True, default=dict)),
                (
                    "mapping_status",
                    models.CharField(
                        choices=[
                            ("uploaded", "Uploaded"),
                            ("parsed", "Parsed"),
                            ("mapped", "Mapped"),
                            ("failed", "Failed"),
                            ("attachment_only", "Attachment only"),
                        ],
                        default="uploaded",
                        max_length=24,
                    ),
                ),
                ("parse_errors", models.JSONField(blank=True, default=dict)),
                ("version", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assets",
                        to="simplequote.dielinetemplate",
                    ),
                ),
            ],
            options={
                "ordering": ["-is_active", "-version", "-created_at"],
                "unique_together": {("template", "version")},
            },
        ),
    ]
