"""
Forms for the events app (admin dashboard usage).

@file   sky_events/apps/events/forms.py
@author slopez.tech
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from django.db.models import Q

from sky_events.apps.camera.models import Camera
from sky_events.apps.notices.models import EventNotice
from sky_events.apps.radio.models import RadioReceiver
from sky_events.apps.station.models import Station

from .models import AstronomicalEvent


class AstronomicalEventForm(forms.ModelForm):
    """
    Form for creating / editing an AstronomicalEvent from the dashboard.

    The ``created_by`` field is set in the view, not in the form.
    """

    detected_at = forms.DateTimeField(
        label=_("Detected at (UTC)"),
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"],
    )

    stations = forms.ModelMultipleChoiceField(
        queryset=Station.objects.order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Stations"),
    )
    cameras = forms.ModelMultipleChoiceField(
        queryset=Camera.objects.select_related("station").order_by("station__name", "name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Cameras"),
    )
    radio_receivers = forms.ModelMultipleChoiceField(
        queryset=RadioReceiver.objects.select_related("station").order_by("station__name", "name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Radio receivers"),
    )
    notices = forms.ModelMultipleChoiceField(
        queryset=EventNotice.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Linked notices"),
        help_text=_("Public reports that correspond to this event."),
    )

    class Meta:
        model = AstronomicalEvent
        fields = [
            "code",
            "name",
            "event_type",
            "status",
            "detected_at",
            "duration_ms",
            "peak_magnitude",
            "altitude_km",
            "velocity_km_s",
            "description",
            "notes",
            "stations",
            "cameras",
            "radio_receivers",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Queryset: unlinked notices + notices already linked to this event
        self.fields["notices"].queryset = EventNotice.objects.filter(
            Q(event__isnull=True) | Q(event=self.instance)
        ).select_related("reviewed_by").order_by("-created_at")
        if self.instance.pk:
            self.fields["notices"].initial = self.instance.notices.values_list("pk", flat=True)

    def save(self, commit: bool = True) -> AstronomicalEvent:
        instance = super().save(commit=commit)
        if commit:
            selected = self.cleaned_data.get("notices", EventNotice.objects.none())
            # Delink notices removed from selection
            instance.notices.exclude(pk__in=selected).update(event=None)
            # Link newly selected notices
            selected.update(event=instance)
        return instance
