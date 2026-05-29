"""
Migration 0003 – hero background style + drop features section fields.

Changes:
- Fix PostgreSQL sequence for webconfig_siteconfig_id_seq (was stuck at 1,
  causing IntegrityError when trying to insert the ES language row).
- Add hero_bg_style CharField with choices.
- Drop features_eyebrow, features_title, features_subtitle (section removed
  from the public site, replaced by the recent-events timeline).
"""

from __future__ import annotations

import django.db.models.deletion
import django.utils.translation
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webconfig", "0002_siteconfig_language_support"),
    ]

    operations = [
        # ── Fix sequence (was stuck at 1 after singleton-era row) ────────
        migrations.RunSQL(
            sql="""
                SELECT setval(
                    pg_get_serial_sequence('webconfig_siteconfig', 'id'),
                    COALESCE((SELECT MAX(id) + 1 FROM webconfig_siteconfig), 2),
                    false
                );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # ── Add hero background style ─────────────────────────────────────
        migrations.AddField(
            model_name="siteconfig",
            name="hero_bg_style",
            field=models.CharField(
                choices=[
                    ("grid", "Grid"),
                    ("dots", "Dots"),
                    ("stars", "Stars"),
                    ("meteors", "Meteors"),
                    ("aurora", "Aurora"),
                    ("nebula", "Nebula"),
                    ("christmas", "Christmas"),
                    ("summer", "Summer"),
                    ("night", "Night sky"),
                    ("day", "Day sky"),
                ],
                default="grid",
                max_length=20,
                verbose_name="hero background style",
            ),
        ),

        # ── Drop features section fields ──────────────────────────────────
        migrations.RemoveField(
            model_name="siteconfig",
            name="features_eyebrow",
        ),
        migrations.RemoveField(
            model_name="siteconfig",
            name="features_title",
        ),
        migrations.RemoveField(
            model_name="siteconfig",
            name="features_subtitle",
        ),
    ]
