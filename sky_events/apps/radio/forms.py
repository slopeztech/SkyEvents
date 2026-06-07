"""
Forms for the radio app (admin dashboard usage).

@file   sky_events/apps/radio/forms.py
@author slopez.tech
"""

from __future__ import annotations

from django import forms

from sky_events.apps.station.models import Station
from sky_events.apps.users.models import UserRole

from .models import RadioReceiver


class RadioReceiverForm(forms.ModelForm):

    class Meta:
        model = RadioReceiver
        fields = [
            "station",
            "name",
            "code",
            "detector",
            "receiver_model",
            "frequency_mhz",
            "bandwidth_khz",
            "antenna_type",
            "polarization",
            "software",
            "status",
            "installed_at",
        ]
        widgets = {
            "installed_at": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if self.request and self.request.user.role != UserRole.ADMIN:
            self.fields["station"].queryset = Station.objects.filter(owner=self.request.user).order_by("name")
        else:
            self.fields["station"].queryset = Station.objects.order_by("name")
        self.fields["station"].label_from_instance = lambda s: f"{s.name} [{s.code}]"
