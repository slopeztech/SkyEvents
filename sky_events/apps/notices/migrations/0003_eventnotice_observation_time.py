from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notices", "0002_eventnotice_event"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventnotice",
            name="observation_time",
            field=models.TimeField(
                blank=True,
                null=True,
                help_text="Local time when the event was observed (leave blank if unknown).",
                verbose_name="observation time",
            ),
        ),
    ]
