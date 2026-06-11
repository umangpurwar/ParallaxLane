from datetime import timedelta

from django.db import migrations
from django.utils.timezone import now


def seed_coupons(apps, schema_editor):
    Coupon = apps.get_model("organisations", "Coupon")
    far_future = now() + timedelta(days=3650)

    samples = [
        {"code": "DEMO-PRO", "plan": "pro", "max_uses": 1000},
        {"code": "EARLY-ACCESS", "plan": "pro", "max_uses": 500},
        {"code": "TEST-ENTERPRISE", "plan": "enterprise", "max_uses": 100},
    ]

    for item in samples:
        Coupon.objects.get_or_create(
            code=item["code"],
            defaults={
                "plan": item["plan"],
                "active": True,
                "max_uses": item["max_uses"],
                "used_count": 0,
                "expires_at": far_future,
            },
        )


def remove_coupons(apps, schema_editor):
    Coupon = apps.get_model("organisations", "Coupon")
    Coupon.objects.filter(code__in=["DEMO-PRO", "EARLY-ACCESS", "TEST-ENTERPRISE"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0006_coupon"),
    ]

    operations = [
        migrations.RunPython(seed_coupons, remove_coupons),
    ]
