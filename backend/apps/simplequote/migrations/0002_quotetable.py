from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("simplequote", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuoteTable",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quote_type", models.CharField(max_length=32)),
                ("table_key", models.CharField(max_length=64)),
                ("rows", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["quote_type", "table_key"],
                "unique_together": {("quote_type", "table_key")},
            },
        ),
    ]
