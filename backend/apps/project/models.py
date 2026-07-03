import uuid

from django.db import models


class Project(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    project_no = models.CharField(max_length=32, unique=True, default="")
    title = models.CharField(max_length=200)
    rfq = models.ForeignKey(
        "rfq.RFQ", null=True, blank=True, on_delete=models.SET_NULL, related_name="projects"
    )
    production_order = models.OneToOneField(
        "rfq.ProductionOrder", null=True, blank=True, on_delete=models.SET_NULL, related_name="project"
    )
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="buyer_projects"
    )
    supplier = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="supplier_projects"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    progress_percent = models.PositiveIntegerField(default=0)
    amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="KRW")
    expected_delivery_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_no():
        return f"MC-PRJ-{uuid.uuid4().hex[:10].upper()}"


class ProjectStage(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=120)
    sort_order = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    planned_date = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]


class ProjectUpdate(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="updates")
    stage = models.ForeignKey(
        ProjectStage, null=True, blank=True, on_delete=models.SET_NULL, related_name="updates"
    )
    author = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="project_updates"
    )
    content = models.TextField()
    is_customer_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ProjectTodo(models.Model):
    ASSIGNEE_CHOICES = [
        ("customer", "Customer"),
        ("supplier", "Supplier"),
        ("platform", "Platform"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="todos")
    title = models.CharField(max_length=200)
    assignee_type = models.CharField(max_length=16, choices=ASSIGNEE_CHOICES, default="customer")
    is_done = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_done", "due_date", "id"]


class ProjectIssue(models.Model):
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("resolved", "Resolved"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="issues")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="medium")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="open")
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="project_issues"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ProjectFile(models.Model):
    CATEGORY_CHOICES = [
        ("design", "Design"),
        ("contract", "Contract"),
        ("report", "Report"),
        ("other", "Other"),
    ]
    VISIBILITY_CHOICES = [
        ("all", "All"),
        ("internal", "Internal"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="files")
    uploader = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="uploaded_project_files"
    )
    file = models.FileField(upload_to="project/%Y/%m/")
    file_name = models.CharField(max_length=255)
    file_category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, default="other")
    visibility = models.CharField(max_length=16, choices=VISIBILITY_CHOICES, default="all")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
