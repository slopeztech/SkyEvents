"""
Forms for the reports app.

@file   sky_events/apps/reports/forms.py
@author slopez.tech
"""

from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from sky_events.apps.camera.models import Camera
from sky_events.apps.radio.models import RadioReceiver
from sky_events.apps.station.models import Station

from .models import ReportFile, StationReport


class StationReportForm(forms.ModelForm):
    """Create / edit a StationReport from the admin dashboard."""

    recorded_at = forms.DateTimeField(
        label=_("Recorded at (UTC)"),
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"],
    )

    class Meta:
        model = StationReport
        fields = [
            "event",
            "station",
            "camera",
            "radio_receiver",
            "recorded_at",
            "duration_ms",
            "status",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Narrow camera/radio choices to the selected station
        station_pk = None
        if self.instance.pk and self.instance.station_id:
            station_pk = self.instance.station_id
        elif self.data.get("station"):
            try:
                station_pk = int(self.data["station"])
            except (ValueError, TypeError):
                pass

        if station_pk:
            self.fields["camera"].queryset = Camera.objects.filter(
                station_id=station_pk
            ).order_by("name")
            self.fields["radio_receiver"].queryset = RadioReceiver.objects.filter(
                station_id=station_pk
            ).order_by("name")
        else:
            self.fields["camera"].queryset = Camera.objects.select_related(
                "station"
            ).order_by("station__name", "name")
            self.fields["radio_receiver"].queryset = RadioReceiver.objects.select_related(
                "station"
            ).order_by("station__name", "name")

        self.fields["event"].queryset = (
            self.fields["event"].queryset.order_by("-detected_at")
        )
        self.fields["event"].empty_label = _("— Not linked yet —")
        self.fields["camera"].empty_label = _("— None (radio only) —")
        self.fields["radio_receiver"].empty_label = _("— None (optical only) —")

    def clean(self):
        cleaned = super().clean()
        camera = cleaned.get("camera")
        radio = cleaned.get("radio_receiver")
        station = cleaned.get("station")

        if camera and camera.station != station:
            self.add_error("camera", _("This camera does not belong to the selected station."))
        if radio and radio.station != station:
            self.add_error("radio_receiver", _("This radio receiver does not belong to the selected station."))
        return cleaned


class ReportFileForm(forms.ModelForm):
    """Inline form for adding / editing a single ReportFile."""

    class Meta:
        model = ReportFile
        fields = ["file_type", "filename", "file_size_bytes", "description", "is_available"]
        widgets = {
            "description": forms.TextInput(),
        }


ReportFileFormSet = inlineformset_factory(
    StationReport,
    ReportFile,
    form=ReportFileForm,
    extra=1,
    can_delete=True,
)
