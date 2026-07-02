from django.db import models

from apps.i18n.fields import I18nJSONField


class Case(models.Model):
    title = I18nJSONField()
    industry = I18nJSONField(default=dict, blank=True)
    summary = I18nJSONField(default=dict, blank=True)
    content = I18nJSONField(default=dict, blank=True)
    cover_image = models.CharField(max_length=512, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class News(models.Model):
    title = I18nJSONField()
    summary = I18nJSONField(default=dict, blank=True)
    content = I18nJSONField(default=dict, blank=True)
    cover_image = models.CharField(max_length=512, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FAQ(models.Model):
    question = I18nJSONField()
    answer = I18nJSONField()
    category = models.CharField(max_length=64, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)


class Download(models.Model):
    title = I18nJSONField()
    file = models.FileField(upload_to="downloads/%Y/%m/")
    file_type = models.CharField(max_length=32, default="pdf")
    locale = models.CharField(max_length=8, default="ko")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)


class ContentPage(models.Model):
    page_key = models.CharField(max_length=120, unique=True)
    title = I18nJSONField(default=dict, blank=True)
    body = I18nJSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class NavItem(models.Model):
    """站点导航（两级：顶级分组 + 子链接）。"""

    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    label = I18nJSONField()
    path = models.CharField(max_length=512, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    open_in_new_tab = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
