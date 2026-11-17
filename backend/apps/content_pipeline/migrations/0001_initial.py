import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PipelineRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("run_date", models.DateField(db_index=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("success", "Success"),
                            ("partial", "Partial"),
                            ("failed", "Failed"),
                            ("disabled", "Disabled"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("target_count", models.PositiveIntegerField(default=10)),
                ("success_count", models.PositiveIntegerField(default=0)),
                ("fail_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-run_date", "-id"],
            },
        ),
        migrations.CreateModel(
            name="UsedYouTubeVideo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("video_id", models.CharField(max_length=32, unique=True)),
                ("keyword", models.CharField(blank=True, max_length=120)),
                ("language", models.CharField(blank=True, max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "blog_post",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="used_youtube_videos",
                        to="blog.blogpost",
                    ),
                ),
            ],
            options={
                "ordering": ["-id"],
            },
        ),
        migrations.CreateModel(
            name="PipelineItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("youtube_video_id", models.CharField(db_index=True, max_length=32)),
                ("keyword", models.CharField(blank=True, max_length=120)),
                ("language", models.CharField(blank=True, max_length=8)),
                ("title", models.CharField(blank=True, max_length=200)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                            ("skipped", "Skipped"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "blog_post",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pipeline_items",
                        to="blog.blogpost",
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="content_pipeline.pipelinerun",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.AddIndex(
            model_name="pipelineitem",
            index=models.Index(fields=["run", "status"], name="cp_item_run_status_idx"),
        ),
    ]
