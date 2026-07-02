from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create default super admin user"

    def handle(self, *args, **options):
        email = "admin@oem.co"
        if User.objects.filter(email=email).exists():
            self.stdout.write("Admin already exists")
            return
        User.objects.create_superuser(email=email, password="Admin123!", name="Super Admin")
        self.stdout.write(self.style.SUCCESS(f"Created admin: {email} / Admin123!"))
