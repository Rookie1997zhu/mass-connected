from django.db import models


class PipelineRun(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_PARTIAL = "partial"
    STATUS_FAILED = "failed"
    STATUS_DISABLED = "disabled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_PARTIAL, "Partial"),
        (STATUS_FAILED, "Failed"),
        (STATUS_DISABLED, "Disabled"),
    ]

    run_date = models.DateField(db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    target_count = models.PositiveIntegerField(default=10)
    success_count = models.PositiveIntegerField(default=0)
    fail_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-run_date", "-id"]

    def __str__(self):
        return f"PipelineRun {self.run_date} {self.status}"


class PipelineItem(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    run = models.ForeignKey(PipelineRun, on_delete=models.CASCADE, related_name="items")
    youtube_video_id = models.CharField(max_length=32, db_index=True)
    keyword = models.CharField(max_length=120, blank=True)
    language = models.CharField(max_length=8, blank=True)
    title = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    blog_post = models.ForeignKey(
        "blog.BlogPost",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pipeline_items",
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["run", "status"], name="cp_item_run_status_idx"),
        ]

    def __str__(self):
        return f"PipelineItem {self.youtube_video_id} {self.status}"


class UsedYouTubeVideo(models.Model):
    video_id = models.CharField(max_length=32, unique=True)
    keyword = models.CharField(max_length=120, blank=True)
    language = models.CharField(max_length=8, blank=True)
    blog_post = models.ForeignKey(
        "blog.BlogPost",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="used_youtube_videos",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.video_id
