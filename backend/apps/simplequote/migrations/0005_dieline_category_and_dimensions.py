from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


CATEGORY_SEEDS = [
    {
        "code": "0200",
        "name_i18n": {
            "zh": "开槽箱",
            "en": "Slotted boxes",
            "ko": "슬롯 박스",
            "ja": "開槽箱",
        },
        "desc_i18n": {
            "zh": "普通纸箱、运输箱，最常用",
            "en": "Common corrugated shipping boxes",
            "ko": "일반 운송 상자",
            "ja": "一般的な輸送箱",
        },
        "sort_order": 20,
    },
    {
        "code": "0400",
        "name_i18n": {
            "zh": "翻盖箱",
            "en": "Folder boxes",
            "ko": "폴더형 박스",
            "ja": "フォルダ箱",
        },
        "desc_i18n": {
            "zh": "飞机盒、文件夹式自锁盒",
            "en": "Mailer and folder-style boxes",
            "ko": "메일러/폴더형 상자",
            "ja": "メーラー・フォルダ型",
        },
        "sort_order": 40,
    },
    {
        "code": "0700",
        "name_i18n": {
            "zh": "插舌盒",
            "en": "Tuck end cartons",
            "ko": "턱 엔드 박스",
            "ja": "差込箱",
        },
        "desc_i18n": {
            "zh": "插舌封底、自动锁底等",
            "en": "Tuck end and auto-lock bottom cartons",
            "ko": "턱 엔드·자동 잠금 박스",
            "ja": "差込・自動ロック底",
        },
        "sort_order": 70,
    },
]


def _board_allowances(thickness_mm):
    t = max(0.1, float(thickness_mm))
    return {
        "internal_lw": (4.0 / 3.0) * t,
        "internal_h": (8.0 / 3.0) * t,
        "external_lw": (2.0 / 3.0) * t,
        "external_h": (4.0 / 3.0) * t,
    }


def _size_triple_from_manufacturing(length_mm, width_mm, height_mm, thickness_mm):
    allow = _board_allowances(thickness_mm)
    return {
        "internal": {
            "length_mm": round(float(length_mm) - allow["internal_lw"], 2),
            "width_mm": round(float(width_mm) - allow["internal_lw"], 2),
            "height_mm": round(float(height_mm) - allow["internal_h"], 2),
        },
        "external": {
            "length_mm": round(float(length_mm) + allow["external_lw"], 2),
            "width_mm": round(float(width_mm) + allow["external_lw"], 2),
            "height_mm": round(float(height_mm) + allow["external_h"], 2),
        },
    }


def seed_categories_and_dimensions(apps, schema_editor):
    DielineCategory = apps.get_model("simplequote", "DielineCategory")
    DielineTemplate = apps.get_model("simplequote", "DielineTemplate")

    category_by_code = {}
    for item in CATEGORY_SEEDS:
        cat, _ = DielineCategory.objects.update_or_create(
            code=item["code"],
            defaults={
                "name_i18n": item["name_i18n"],
                "desc_i18n": item["desc_i18n"],
                "sort_order": item["sort_order"],
                "is_active": True,
            },
        )
        category_by_code[item["code"]] = cat


def unseed_categories(apps, schema_editor):
    DielineCategory = apps.get_model("simplequote", "DielineCategory")
    DielineTemplate = apps.get_model("simplequote", "DielineTemplate")
    DielineTemplate.objects.update(category_id=None)
    DielineCategory.objects.filter(code__in=["0200", "0400", "0700"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("simplequote", "0004_folding_shipping_template"),
    ]

    operations = [
        migrations.CreateModel(
            name="DielineCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=16, unique=True)),
                ("name_i18n", models.JSONField(blank=True, default=dict)),
                ("desc_i18n", models.JSONField(blank=True, default=dict)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "code"],
            },
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="default_external_height_mm",
            field=models.DecimalField(decimal_places=2, default=100, max_digits=10),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="default_external_length_mm",
            field=models.DecimalField(decimal_places=2, default=200, max_digits=10),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="default_external_width_mm",
            field=models.DecimalField(decimal_places=2, default=150, max_digits=10),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="default_internal_height_mm",
            field=models.DecimalField(decimal_places=2, default=100, max_digits=10),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="default_internal_length_mm",
            field=models.DecimalField(decimal_places=2, default=200, max_digits=10),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="default_internal_width_mm",
            field=models.DecimalField(decimal_places=2, default=150, max_digits=10),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="default_manufacturing_height_mm",
            field=models.DecimalField(decimal_places=2, default=100, max_digits=10),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="default_manufacturing_length_mm",
            field=models.DecimalField(decimal_places=2, default=200, max_digits=10),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="default_manufacturing_width_mm",
            field=models.DecimalField(decimal_places=2, default=150, max_digits=10),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="templates",
                to="simplequote.dielinecategory",
            ),
        ),
        migrations.RunPython(seed_categories_and_dimensions, unseed_categories),
    ]
