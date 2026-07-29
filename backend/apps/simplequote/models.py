import uuid

from django.db import models


class QuoteTable(models.Model):
    """简单报价多列表格（费率阶梯、计分表、定价行等），后台可维护。"""

    quote_type = models.CharField(max_length=32)
    table_key = models.CharField(max_length=64)
    rows = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["quote_type", "table_key"]
        unique_together = [("quote_type", "table_key")]


class QuoteParam(models.Model):
    """简单报价参数（材料单价、机时费率、模具等级价等），后台可维护。"""

    quote_type = models.CharField(max_length=32)
    param_key = models.CharField(max_length=64)
    label = models.CharField(max_length=120, blank=True)
    value = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    unit = models.CharField(max_length=32, blank=True)
    note = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["quote_type", "param_key"]
        unique_together = [("quote_type", "param_key")]


class DielineCategory(models.Model):
    """刀版盒型分类（管理员可维护）。"""

    code = models.CharField(max_length=16, unique=True)
    name_i18n = models.JSONField(default=dict, blank=True)
    desc_i18n = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "code"]

    def __str__(self):
        return self.code


class DielineTemplate(models.Model):
    """刀版参数化模板（DB 驱动，管理员可维护）。"""

    ENGINE_CHOICES = [
        ("slotted_rsc", "Slotted RSC"),
        ("folding_shipping", "Folding shipping box"),
        ("mailer_folder", "Mailer folder"),
        ("tuck_end", "Tuck end"),
        ("auto_lock_bottom", "Auto lock bottom"),
    ]
    FLUTE_CHOICES = [
        ("e", "E flute"),
        ("b", "B flute"),
        ("c", "C flute"),
        ("bc", "BC flute"),
        ("none", "Non-flute"),
    ]
    MATERIAL_CHOICES = [
        ("corrugated", "Corrugated"),
        ("white_card", "White card"),
        ("kraft", "Kraft"),
        ("coated", "Coated"),
    ]
    DIMENSION_TYPE_CHOICES = [
        ("internal", "Internal"),
        ("external", "External"),
        ("manufacturing", "Manufacturing"),
    ]
    PRIORITY_CHOICES = [
        ("P0", "P0"),
        ("P1", "P1"),
    ]

    code = models.CharField(max_length=16, unique=True)
    category = models.ForeignKey(
        DielineCategory,
        on_delete=models.PROTECT,
        related_name="templates",
        null=True,
        blank=True,
    )
    category_code = models.CharField(max_length=16)
    engine_key = models.CharField(max_length=32, choices=ENGINE_CHOICES)
    name_i18n = models.JSONField(default=dict, blank=True)
    desc_i18n = models.JSONField(default=dict, blank=True)
    default_length_mm = models.DecimalField(max_digits=10, decimal_places=2, default=200)
    default_width_mm = models.DecimalField(max_digits=10, decimal_places=2, default=150)
    default_height_mm = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    default_manufacturing_length_mm = models.DecimalField(max_digits=10, decimal_places=2, default=200)
    default_manufacturing_width_mm = models.DecimalField(max_digits=10, decimal_places=2, default=150)
    default_manufacturing_height_mm = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    default_internal_length_mm = models.DecimalField(max_digits=10, decimal_places=2, default=200)
    default_internal_width_mm = models.DecimalField(max_digits=10, decimal_places=2, default=150)
    default_internal_height_mm = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    default_external_length_mm = models.DecimalField(max_digits=10, decimal_places=2, default=200)
    default_external_width_mm = models.DecimalField(max_digits=10, decimal_places=2, default=150)
    default_external_height_mm = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    default_thickness_mm = models.DecimalField(max_digits=8, decimal_places=2, default=1.5)
    default_glue_tab_mm = models.DecimalField(max_digits=8, decimal_places=2, default=25)
    flute_type = models.CharField(max_length=8, choices=FLUTE_CHOICES, default="b")
    material_type = models.CharField(max_length=16, choices=MATERIAL_CHOICES, default="corrugated")
    default_dimension_type = models.CharField(
        max_length=16, choices=DIMENSION_TYPE_CHOICES, default="internal"
    )
    min_length_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_length_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_width_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_width_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_height_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_height_mm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    slot_gap_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    crease_gap_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    flap_gap_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    structure_params = models.JSONField(default=dict, blank=True)
    allowances = models.JSONField(default=dict, blank=True)
    production_asset = models.FileField(
        upload_to="dieline_production/%Y/%m/", null=True, blank=True
    )
    priority = models.CharField(max_length=8, choices=PRIORITY_CHOICES, default="P0")
    quote_enabled = models.BooleanField(default=True)
    preview_enabled = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    thumbnail = models.ImageField(upload_to="dieline_template/%Y/%m/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"FEFCO {self.code}"


class DielineTemplateAsset(models.Model):
    """真实刀版资产版本：解析结果 + 人工参数映射。"""

    FORMAT_CHOICES = [
        ("dxf", "DXF"),
        ("svg", "SVG"),
        ("ai", "AI"),
        ("pdf", "PDF"),
    ]
    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("parsed", "Parsed"),
        ("mapped", "Mapped"),
        ("failed", "Failed"),
        ("attachment_only", "Attachment only"),
    ]

    template = models.ForeignKey(
        DielineTemplate,
        on_delete=models.CASCADE,
        related_name="assets",
    )
    source_file = models.FileField(upload_to="dieline_assets/%Y/%m/")
    source_format = models.CharField(max_length=8, choices=FORMAT_CHOICES)
    parsed_geometry = models.JSONField(default=dict, blank=True)
    mapping_schema = models.JSONField(default=dict, blank=True)
    base_dimensions = models.JSONField(default=dict, blank=True)
    mapping_status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="uploaded")
    parse_errors = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-version", "-created_at"]
        unique_together = [("template", "version")]

    def __str__(self):
        return f"{self.template.code} asset v{self.version}"


class Print3dSliceJob(models.Model):
    """Temporary 3D print slice job: upload → PrusaSlicer → weight/time for quoting."""

    STATUS_PENDING = "pending"
    STATUS_CONVERTING = "converting"
    STATUS_SLICING = "slicing"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONVERTING, "Converting STEP"),
        (STATUS_SLICING, "Slicing"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
    ]

    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="print3d_slice_jobs"
    )
    source_file = models.FileField(
        upload_to="print3d_slice/%Y/%m/%d/", null=True, blank=True
    )
    original_filename = models.CharField(max_length=255, blank=True)
    file_ext = models.CharField(max_length=16, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    inputs = models.JSONField(default=dict, blank=True)
    config_snapshot = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    # deprecated: 新任务写入 preview_file，不再填充大 JSON
    preview_mesh = models.JSONField(null=True, blank=True)
    preview_file = models.FileField(
        upload_to="print3d/preview/%Y/%m/", null=True, blank=True
    )
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    celery_task_id = models.CharField(max_length=64, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    source_cleared_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_failed(self, code: str, message: str):
        self.status = self.STATUS_FAILED
        self.error_code = code[:64]
        self.error_message = (message or "")[:500]
        self.save(
            update_fields=[
                "status",
                "error_code",
                "error_message",
                "updated_at",
            ]
        )


class SimpleQuote(models.Model):
    TYPE_CHOICES = [
        ("injection", "Injection Mold"),
        ("print3d", "3D Printing"),
        ("pcba", "PCBA Assembly"),
        ("pcb", "PCB Development"),
        ("software", "Software"),
        ("ic", "IC Design"),
        ("paper_box", "Paper Box"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("calculated", "Calculated"),
        ("pdf_generated", "PDF Generated"),
        ("converted", "Converted to Detail"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    quote_no = models.CharField(max_length=32, unique=True)
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="simple_quotes"
    )
    quote_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    product_name = models.CharField(max_length=200, blank=True)
    inputs = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    total_amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="KRW")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="calculated")
    valid_until = models.DateField(null=True, blank=True)
    points_spent = models.PositiveIntegerField(default=0)
    pdf = models.FileField(upload_to="simple_quote/%Y/%m/", null=True, blank=True)
    converted_rfq = models.ForeignKey(
        "rfq.RFQ", null=True, blank=True, on_delete=models.SET_NULL, related_name="from_simple_quotes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_no():
        return f"MC-QT-{uuid.uuid4().hex[:10].upper()}"
