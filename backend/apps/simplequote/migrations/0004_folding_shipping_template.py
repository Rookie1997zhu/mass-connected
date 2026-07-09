from decimal import Decimal

from django.db import migrations, models


FOLDING_SHIPPING_I18N = {
    "name_i18n": {
        "zh": "折叠运输箱",
        "en": "Folding Shipping Box",
        "ko": "접이식 운송 상자",
        "ja": "折りたたみ輸送箱",
    },
    "desc_i18n": {
        "zh": "互锁底开槽运输箱，适用于重型包装运输",
        "en": "Slotted shipping box with interlocking bottom flaps",
        "ko": "인터록 바닥 개槽 운송 상자",
        "ja": "インターロック底の開槽輸送箱",
    },
}


def seed_folding_shipping_template(apps, schema_editor):
    pass


def unseed_folding_shipping_template(apps, schema_editor):
    DielineTemplate = apps.get_model("simplequote", "DielineTemplate")
    DielineTemplate.objects.filter(code="0210").delete()
    DielineTemplate.objects.filter(code="0427").update(sort_order=2)
    DielineTemplate.objects.filter(code="0713").update(sort_order=3)
    DielineTemplate.objects.filter(code="0716").update(sort_order=4)


class Migration(migrations.Migration):
    dependencies = [
        ("simplequote", "0003_dielinetemplate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dielinetemplate",
            name="engine_key",
            field=models.CharField(
                choices=[
                    ("slotted_rsc", "Slotted RSC"),
                    ("folding_shipping", "Folding shipping box"),
                    ("mailer_folder", "Mailer folder"),
                    ("tuck_end", "Tuck end"),
                    ("auto_lock_bottom", "Auto lock bottom"),
                ],
                max_length=32,
            ),
        ),
        migrations.RunPython(seed_folding_shipping_template, unseed_folding_shipping_template),
    ]
