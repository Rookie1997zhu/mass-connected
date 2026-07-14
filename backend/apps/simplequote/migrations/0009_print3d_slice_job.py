from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("simplequote", "0008_remove_builtin_dieline_templates"),
    ]

    operations = [
        migrations.CreateModel(
            name="Print3dSliceJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_file", models.FileField(blank=True, null=True, upload_to="print3d_slice/%Y/%m/%d/")),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("file_ext", models.CharField(blank=True, max_length=16)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("converting", "Converting STEP"),
                            ("slicing", "Slicing"),
                            ("done", "Done"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("inputs", models.JSONField(blank=True, default=dict)),
                ("config_snapshot", models.JSONField(blank=True, default=dict)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("preview_mesh", models.JSONField(blank=True, null=True)),
                ("error_code", models.CharField(blank=True, max_length=64)),
                ("error_message", models.CharField(blank=True, max_length=500)),
                ("celery_task_id", models.CharField(blank=True, max_length=64)),
                ("expires_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("source_cleared_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "buyer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="print3d_slice_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
