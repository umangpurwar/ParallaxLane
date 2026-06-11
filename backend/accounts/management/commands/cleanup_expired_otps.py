from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from accounts.models import EmailOTP


class Command(BaseCommand):
    help = "Delete EmailOTP records older than the expiry window (default 24 hours)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Delete OTP records older than this many hours (default: 24).",
        )

    def handle(self, *args, **options):
        cutoff = now() - timedelta(hours=options["hours"])
        deleted, _ = EmailOTP.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired OTP record(s)."))
