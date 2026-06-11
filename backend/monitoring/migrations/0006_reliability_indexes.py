from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("monitoring", "0005_alter_screenshot_image"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS violation_timestamp_desc_idx "
                "ON monitoring_violation (timestamp DESC);"
            ),
            reverse_sql="DROP INDEX IF EXISTS violation_timestamp_desc_idx;",
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS screenshot_timestamp_desc_idx "
                "ON monitoring_screenshot (timestamp DESC);"
            ),
            reverse_sql="DROP INDEX IF EXISTS screenshot_timestamp_desc_idx;",
        ),
    ]
