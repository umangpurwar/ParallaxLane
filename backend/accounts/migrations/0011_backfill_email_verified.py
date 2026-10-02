from django.db import migrations


def backfill(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    # Every account active today completed verification (or was created by an admin).
    User.objects.filter(is_active=True).update(email_verified=True)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0010_user_email_verified_userdevice")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
