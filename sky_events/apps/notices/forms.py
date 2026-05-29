"""
Forms for the notices app.

@file   sky_events/apps/notices/forms.py
@author slopez.tech
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import EventNotice, EventType


class EventNoticeForm(forms.ModelForm):
    """
    Public form for submitting an event notice.

    Only exposes the fields that a visitor should fill in.
    Status, reviewer and timestamps are managed internally.
    """

    observation_date = forms.DateField(
        label=_("Observation date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = EventNotice
        fields = ["name", "email", "event_type", "observation_date", "location", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add a blank default choice to the event_type select
        self.fields["event_type"].choices = [("", _("— Select event type —"))] + list(
            EventType.choices
        )
        self.fields["event_type"].initial = ""
