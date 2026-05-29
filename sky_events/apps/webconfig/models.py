"""
Singleton model for site-wide configuration.

There is always exactly one row (pk=1).  Use SiteConfig.load() to retrieve it.

@file   sky_events/apps/webconfig/models.py
@author slopez.tech
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class HeroBgStyle(models.TextChoices):
    GRID       = "grid",       _("Grid")
    DOTS       = "dots",       _("Dots")
    STARS      = "stars",      _("Stars")
    METEORS    = "meteors",    _("Meteors")
    AURORA     = "aurora",     _("Aurora")
    NEBULA     = "nebula",     _("Nebula")
    CHRISTMAS  = "christmas",  _("Christmas")
    SUMMER     = "summer",     _("Summer")
    NIGHT      = "night",      _("Night sky")
    DAY        = "day",        _("Day sky")
    # — new styles —
    NEON       = "neon",       _("Neon")
    HUMO       = "humo",       _("Smoke")
    STARTRAILS = "startrails", _("Star trails")
    ORBITS     = "orbits",     _("Orbits")
    PULSE      = "pulse",      _("Pulse")
    WAVE       = "wave",       _("Wave")
    GEO        = "geo",        _("Geo")
    VOID       = "void",       _("Void")
    PLASMA     = "plasma",     _("Plasma")
    RAIN       = "rain",       _("Rain")
    BOKEH      = "bokeh",      _("Bokeh")
    HORIZON    = "horizon",    _("Horizon")
    PRISM      = "prism",      _("Prism")
    GLITCH     = "glitch",     _("Glitch")
    LATTICE    = "lattice",    _("Lattice")
    MATRIX     = "matrix",    _("Matrix")
    CARWINDOW  = "carwindow",  _("Car window")
    COMET      = "comet",      _("Comet")
    FIREFLY    = "firefly",    _("Firefly")
    CIRCUIT    = "circuit",    _("Circuit")


class SiteConfig(models.Model):
    """Per-language site configuration.  One row per language code."""

    language_code = models.CharField(
        _("language"),
        max_length=10,
        unique=True,
        default="en",
        help_text=_("ISO 639-1 language code this configuration applies to."),
    )

    # ── Site identity ────────────────────────────────────────────────────────
    site_name = models.CharField(
        _("site name"),
        max_length=100,
        default="SkyEvents",
        help_text=_("Display name of the application."),
    )
    page_title = models.CharField(
        _("page title / tagline"),
        max_length=200,
        default="Automated meteor observation network",
        help_text=_("Shown in the browser tab and meta description."),
    )

    # ── Hero section ─────────────────────────────────────────────────────────
    hero_badge = models.CharField(
        _("hero badge"),
        max_length=100,
        default="Meteor detection network",
        help_text=_("Short label shown in the badge above the hero title."),
    )
    hero_pre_highlight = models.CharField(
        _("hero title — before highlight"),
        max_length=150,
        default="Observe the",
    )
    hero_highlight = models.CharField(
        _("hero title — highlighted word"),
        max_length=50,
        default="cosmos",
        help_text=_("This word will be rendered with the accent gradient."),
    )
    hero_post_highlight = models.CharField(
        _("hero title — after highlight"),
        max_length=150,
        default="automatically.",
    )
    hero_subtitle = models.TextField(
        _("hero subtitle"),
        default=(
            "SkyEvents coordinates your network of stations, cameras, and radio receivers "
            "to detect and classify astronomical events in real time."
        ),
    )

    hero_bg_style = models.CharField(
        _("hero background style"),
        max_length=20,
        choices=HeroBgStyle.choices,
        default=HeroBgStyle.GRID,
        help_text=_("Visual style for the hero section background."),
    )

    # ── Stats bar ─────────────────────────────────────────────────────────────
    stats_stations_label = models.CharField(
        _("stats: stations label"),
        max_length=100,
        default="Observation stations",
    )
    stats_cameras_label = models.CharField(
        _("stats: cameras label"),
        max_length=100,
        default="Cameras supported",
    )
    stats_radios_label = models.CharField(
        _("stats: radios label"),
        max_length=100,
        default="Radio receivers",
    )
    stats_events_label = models.CharField(
        _("stats: events label"),
        max_length=100,
        default="Events detected",
    )

    # ── CTA section ──────────────────────────────────────────────────────────
    cta_title = models.CharField(
        _("CTA title"),
        max_length=200,
        default="Ready to join the network?",
    )
    cta_subtitle = models.TextField(
        _("CTA subtitle"),
        default="Sign in to access your dashboard and start monitoring your stations.",
    )

    # ── Contact / footer ─────────────────────────────────────────────────────
    contact_email = models.EmailField(
        _("contact e-mail"),
        blank=True,
        default="",
        help_text=_("Optional public contact address shown in the footer."),
    )
    footer_text = models.CharField(
        _("footer text"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Optional extra line displayed at the bottom of the page."),
    )

    class Meta:
        verbose_name = _("site configuration")
        verbose_name_plural = _("site configuration")

    def __str__(self) -> str:  # pragma: no cover
        return f"Site configuration ({self.language_code})"

    # ── Per-language access ──────────────────────────────────────────────────

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)

    @classmethod
    def load(cls, language_code: str = "en") -> "SiteConfig":
        """Return the config for *language_code*, creating it with defaults if absent."""
        obj, _ = cls.objects.get_or_create(language_code=language_code)
        return obj
