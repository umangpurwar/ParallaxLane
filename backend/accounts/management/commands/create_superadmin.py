"""Provision the platform super admin from environment variables.

    SUPERADMIN_EMAIL=... SUPERADMIN_PASSWORD=... python manage.py create_superadmin

Safe to run on every deploy: an existing super admin is left untouched unless
--reset-password is given. An existing non-admin account with that email is
never promoted silently; that needs --promote-existing.
"""

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create (or keep) the Parallax Lane super admin from SUPERADMIN_EMAIL / SUPERADMIN_PASSWORD."

    def add_arguments(self, parser):
        parser.add_argument("--reset-password", action="store_true",
                            help="Set SUPERADMIN_PASSWORD on the existing super admin.")
        parser.add_argument("--promote-existing", action="store_true",
                            help="Turn an existing ordinary account with this email into the super admin.")

    def handle(self, *args, **options):
        User = get_user_model()
        email = (os.environ.get("SUPERADMIN_EMAIL") or "").strip().lower()
        password = os.environ.get("SUPERADMIN_PASSWORD") or ""
        if not email:
            raise CommandError("SUPERADMIN_EMAIL is not set.")

        with transaction.atomic():
            user = User.objects.select_for_update().filter(email__iexact=email).first()
            if user is not None and user.is_superuser:
                if options["reset_password"]:
                    self._check_password(password, user)
                    user.set_password(password)
                    user.save(update_fields=["password"])
                    self.stdout.write(self.style.SUCCESS(f"Password reset for super admin {email}."))
                else:
                    self.stdout.write(f"Super admin {email} already exists; nothing changed.")
                return

            if user is not None and not options["promote_existing"]:
                raise CommandError(
                    f"An ordinary account already uses {email}. Choose another SUPERADMIN_EMAIL, "
                    "or rerun with --promote-existing if you really mean to promote it."
                )

            self._check_password(password, user)
            if user is None:
                user = User(email=email, username=email, name="Super Admin")
            if user.memberships.exists() if user.pk else False:
                raise CommandError("That account belongs to an organisation and cannot become the super admin.")
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.email_verified = True
            user.set_password(password)
            user.save()
        self.stdout.write(self.style.SUCCESS(f"Super admin {email} is ready."))

    @staticmethod
    def _check_password(password, user):
        if not password:
            raise CommandError("SUPERADMIN_PASSWORD is not set.")
        try:
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError("SUPERADMIN_PASSWORD is too weak: " + " ".join(exc.messages))
