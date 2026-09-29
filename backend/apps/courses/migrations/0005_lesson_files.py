import os

import django.db.models.deletion
from django.db import migrations, models


def move_attachments_to_files(apps, schema_editor):
    """Each lesson's single old `attachment` becomes its first LessonFile."""
    Lesson = apps.get_model("courses", "Lesson")
    LessonFile = apps.get_model("courses", "LessonFile")
    for lesson in Lesson.objects.exclude(attachment="").exclude(attachment__isnull=True):
        name = os.path.basename(lesson.attachment.name)
        try:
            size = lesson.attachment.size
        except Exception:  # file missing from storage — keep the row, size unknown
            size = 0
        LessonFile.objects.create(
            lesson=lesson,
            title=name.rsplit(".", 1)[0],
            file=lesson.attachment.name,
            original_name=name,
            size_bytes=size,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0004_classsession_room_slug'),
    ]

    operations = [
        migrations.CreateModel(
            name='LessonFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(blank=True, max_length=255)),
                ('file', models.FileField(upload_to='lesson_files/')),
                ('original_name', models.CharField(max_length=255)),
                ('size_bytes', models.PositiveBigIntegerField(default=0)),
                ('lesson', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='courses.lesson')),
            ],
            options={
                'ordering': ('created_at',),
            },
        ),
        migrations.RunPython(move_attachments_to_files, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='lesson',
            name='attachment',
        ),
    ]
