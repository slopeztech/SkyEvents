from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webconfig", "0007_alter_siteconfig_hero_bg_style"),
    ]

    operations = [
        migrations.AddField(
            model_name="siteconfig",
            name="footer_tagline",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Short tagline displayed next to the logo in the footer (leave blank to hide).",
                max_length=120,
                verbose_name="footer tagline",
            ),
        ),
    ]
