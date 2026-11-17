"""手动执行一轮内容流水线（同步串行，便于联调）。"""

from django.core.management.base import BaseCommand

from apps.content_pipeline.services import run_daily_batch


class Command(BaseCommand):
    help = "Run one YouTube→blog content pipeline batch synchronously"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignore CONTENT_PIPELINE_ENABLED=false and run anyway",
        )

    def handle(self, *args, **options):
        if options.get("force"):
            from django.conf import settings

            settings.CONTENT_PIPELINE_ENABLED = True
            self.stdout.write(self.style.WARNING("Forced CONTENT_PIPELINE_ENABLED=true for this run"))

        result = run_daily_batch(sync=True)
        self.stdout.write(self.style.SUCCESS(str(result)))
