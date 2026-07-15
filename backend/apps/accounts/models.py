from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "super_admin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("super_admin", "Super Admin"),
        ("operator", "Operator"),
        ("sales", "Sales"),
        ("member", "Member"),
        ("factory", "Factory"),
    ]
    MEMBER_TYPE_CHOICES = [
        ("individual", "Individual"),
        ("enterprise", "Enterprise"),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    member_type = models.CharField(
        max_length=20, choices=MEMBER_TYPE_CHOICES, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class FactoryProfile(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("suspended", "Suspended"),
        ("blacklist", "Blacklist"),
        ("observing", "Observing"),
        ("priority", "Priority"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="factory_profile")
    company_name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=80, blank=True)
    region = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    intro = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    payment_terms = models.CharField(max_length=200, blank=True)
    established_year = models.PositiveIntegerField(null=True, blank=True)
    employee_scale = models.CharField(max_length=64, blank=True)
    factory_area_sqm = models.PositiveIntegerField(null=True, blank=True)
    main_products = models.TextField(blank=True)
    monthly_capacity = models.CharField(max_length=200, blank=True)
    quality_certifications = models.TextField(blank=True)
    equipment_summary = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    business_license = models.FileField(upload_to="supplier/license/%Y/%m/", null=True, blank=True)
    processes = models.ManyToManyField(
        "rfq.ServiceCategory", blank=True, related_name="factory_profiles"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.company_name


class SupplierTag(models.Model):
    profile = models.ForeignKey(FactoryProfile, on_delete=models.CASCADE, related_name="tags")
    tag_name = models.CharField(max_length=64)

    class Meta:
        ordering = ["tag_name", "id"]
        unique_together = [("profile", "tag_name")]

    def __str__(self):
        return self.tag_name


class SupplierAttachment(models.Model):
    CATEGORY_CHOICES = [
        ("qualification", "Qualification"),
        ("company_profile", "Company Profile"),
        ("certification", "Certification"),
        ("equipment", "Equipment"),
        ("case", "Case"),
        ("other", "Other"),
    ]

    profile = models.ForeignKey(FactoryProfile, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="supplier/attachments/%Y/%m/")
    file_name = models.CharField(max_length=255)
    category = models.CharField(max_length=32, blank=True, default="qualification", choices=CATEGORY_CHOICES)
    is_public = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.file_name
