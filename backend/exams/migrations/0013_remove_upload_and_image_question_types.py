# Removes the image_based and file_upload question types and the unused
# Answer.file_upload column. Stops instead of deleting data if any question
# still uses one of the removed types.

from django.db import migrations, models


REMOVED_TYPES = ("image_based", "file_upload")


def refuse_if_removed_types_exist(apps, schema_editor):
    Question = apps.get_model("exams", "Question")
    leftover = list(
        Question.objects.filter(question_type__in=REMOVED_TYPES).values_list("id", "exam_id")[:20]
    )
    if leftover:
        raise RuntimeError(
            "These questions (question id, exam id) still use image_based or file_upload: "
            f"{leftover}. Change their type or delete those exams, then run migrate again."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0012_attempt_device_state_answer_restrict'),
    ]

    operations = [
        migrations.RunPython(refuse_if_removed_types_exist, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='answer',
            name='file_upload',
        ),
        migrations.AlterField(
            model_name='question',
            name='question_type',
            field=models.CharField(choices=[('mcq', 'Multiple Choice'), ('true_false', 'True/False'), ('short_answer', 'Short Answer')], default='mcq', max_length=20),
        ),
    ]
