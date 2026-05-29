"""
Migration: add language_code to SiteConfig and convert from singleton to per-language rows.

@file   sky_events/apps/webconfig/migrations/0002_siteconfig_language_support.py
@author slopez.tech
"""

from __future__ import annotations

from django.db import migrations, models


def migrate_existing_row_to_en(apps, schema_editor):
    """Tag the existing singleton row (pk=1) as English."""
    SiteConfig = apps.get_model("webconfig", "SiteConfig")
    SiteConfig.objects.filter(pk=1).update(language_code="en")


class Migration(migrations.Migration):
    dependencies = [
        ("webconfig", "0001_initial"),
    ]

    operations = [
        # 1. Add language_code (nullable first so the column can be created)
        migrations.AddField(
            model_name="siteconfig",
            name="language_code",
            field=models.CharField(
                default="en",
                max_length=10,
                verbose_name="language",
            ),
        ),
        # 2. Backfill the existing row
        migrations.RunPython(migrate_existing_row_to_en, migrations.RunPython.noop),
        # 3. Now make it unique
        migrations.AlterField(
            model_name="siteconfig",
            name="language_code",
            field=models.CharField(
                default="en",
                help_text="ISO 639-1 language code this configuration applies to.",
                max_length=10,
                unique=True,
                verbose_name="language",
            ),
        ),
    ]
