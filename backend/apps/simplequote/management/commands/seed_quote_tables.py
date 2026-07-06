from django.core.management.base import BaseCommand

from apps.simplequote.models import QuoteParam, QuoteTable
from apps.simplequote.table_data import (
    PCBA_PARAM_DEFAULTS,
    PCBA_PARAM_META,
    PCB_PARAM_DEFAULTS,
    PCB_PARAM_META,
    QUOTE_TABLE_SEED,
    SHIPPING_PARAM_DEFAULTS,
    SHIPPING_PARAM_META,
)


class Command(BaseCommand):
    help = "Seed QuoteTable rows and quote_type-specific QuoteParam defaults (idempotent)."

    def handle(self, *args, **options):
        table_count = 0
        for quote_type, table_key, rows in QUOTE_TABLE_SEED:
            _, created = QuoteTable.objects.update_or_create(
                quote_type=quote_type,
                table_key=table_key,
                defaults={"rows": rows, "is_active": True},
            )
            if created:
                table_count += 1

        param_count = self._seed_params("shipping", SHIPPING_PARAM_DEFAULTS, SHIPPING_PARAM_META)
        param_count += self._seed_params("pcba", PCBA_PARAM_DEFAULTS, PCBA_PARAM_META)
        param_count += self._seed_params("pcb", PCB_PARAM_DEFAULTS, PCB_PARAM_META)

        self.stdout.write(
            self.style.SUCCESS(
                f"QuoteTable seed done (new tables: {table_count}, new params: {param_count})."
            )
        )

    def _seed_params(self, quote_type, defaults, meta):
        created = 0
        for key, value in defaults.items():
            label, unit = meta.get(key, (key, ""))
            _, was_created = QuoteParam.objects.get_or_create(
                quote_type=quote_type,
                param_key=key,
                defaults={
                    "label": label,
                    "value": value,
                    "unit": unit,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
        return created
