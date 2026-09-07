from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_geometry_mode(apps, schema_editor):
    DielineTemplate = apps.get_model("simplequote", "DielineTemplate")
    formula_engines = {
        "slotted_rsc",
        "folding_shipping",
        "mailer_folder",
        "tuck_end",
        "auto_lock_bottom",
    }
    for tpl in DielineTemplate.objects.all():
        # Existing sample assets are custom drawings; only pure formula templates stay formula.
        has_mapped = tpl.assets.filter(is_active=True, mapping_status="mapped").exists()
        if has_mapped and tpl.engine_key in formula_engines:
            # Sample template 01 was mis-tagged slotted_rsc but is a tray with arc lid.
            tpl.geometry_mode = "fixed_asset"
        elif tpl.engine_key in formula_engines:
            tpl.geometry_mode = "formula"
        else:
            tpl.geometry_mode = "fixed_asset"
        tpl.save(update_fields=["geometry_mode"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("simplequote", "0011_print3d_preview_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="dielinetemplate",
            name="geometry_mode",
            field=models.CharField(
                choices=[("formula", "Formula"), ("fixed_asset", "Fixed asset")],
                default="formula",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="dielinetemplate",
            name="points_cost",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RenameField(
            model_name="dielinetemplate",
            old_name="quote_enabled",
            new_name="purchase_enabled",
        ),
        migrations.AddField(
            model_name="dielinetemplateasset",
            name="calibrated_height_mm",
            field=models.DecimalField(
                blank=True, decimal_places=4, max_digits=12, null=True
            ),
        ),
        migrations.AddField(
            model_name="dielinetemplateasset",
            name="calibrated_width_mm",
            field=models.DecimalField(
                blank=True, decimal_places=4, max_digits=12, null=True
            ),
        ),
        migrations.CreateModel(
            name="DielineTemplatePurchase",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("points_spent", models.PositiveIntegerField(default=0)),
                ("transaction_no", models.CharField(blank=True, default="", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="purchases",
                        to="simplequote.dielinetemplate",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dieline_purchases",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="dielinetemplatepurchase",
            constraint=models.UniqueConstraint(
                fields=("user", "template"),
                name="uniq_dieline_purchase_user_template",
            ),
        ),
        migrations.RunPython(backfill_geometry_mode, noop_reverse),
    ]
