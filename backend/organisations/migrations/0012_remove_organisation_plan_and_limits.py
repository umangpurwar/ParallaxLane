# Removes the organisation plan (free/pro/enterprise), the plan-based limits and
# the unused proctoring_enabled feature flag that only plan usage reporting read.
# Data loss: the stored plan, max_* and proctoring_enabled values are dropped and cannot be recovered
# by reversing this migration (reversal recreates the columns with their defaults).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0011_organisation_contact_phone_organisation_description_and_more"),
    ]

    operations = [
        migrations.RemoveField(model_name="organisation", name="plan"),
        migrations.RemoveField(model_name="organisation", name="max_exams"),
        migrations.RemoveField(model_name="organisation", name="max_candidates"),
        migrations.RemoveField(model_name="organisation", name="max_admins"),
        migrations.RemoveField(model_name="organisation", name="max_invigilators"),
        migrations.RemoveField(model_name="organisation", name="proctoring_enabled"),
    ]
