"""
Form for editing the SiteConfig singleton.

@file   sky_events/apps/webconfig/forms.py
@author slopez.tech
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import SiteConfig


class SiteConfigForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        exclude = ["id", "language_code"]
        widgets = {
            "hero_subtitle": forms.Textarea(attrs={"rows": 3}),
            "cta_subtitle": forms.Textarea(attrs={"rows": 3}),
            "hero_bg_style": forms.RadioSelect,
        }
        help_texts = {
            "hero_pre_highlight": _("First part of the hero headline, e.g. 'Observe the'"),
            "hero_post_highlight": _("Last part of the hero headline, e.g. 'automatically.'"),
        }
