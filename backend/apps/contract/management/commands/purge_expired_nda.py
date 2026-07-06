from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.contract.models import NdaSignature


class Command(BaseCommand):
    help = "Delete NDA PDF files past retention_delete_at (1 year retention)."

    def handle(self, *args, **options):
        now = timezone.now()
        qs = NdaSignature.objects.filter(retention_delete_at__lte=now).exclude(pdf="")
        count = 0
        for sig in qs:
            if sig.pdf:
                sig.pdf.delete(save=False)
                sig.pdf = None
                sig.save(update_fields=["pdf", "updated_at"])
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Purged {count} expired NDA PDF(s)."))
