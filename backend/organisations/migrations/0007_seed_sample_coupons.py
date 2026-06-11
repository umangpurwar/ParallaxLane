from django.db import migrations


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0006_coupon"),
    ]

    operations = [
        migrations.RunPython(noop, noop),
    ]
