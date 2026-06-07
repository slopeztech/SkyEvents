"""
Forms for the camera app (admin dashboard usage).

@file   sky_events/apps/camera/forms.py
@author slopez.tech
"""

from __future__ import annotations

from django import forms

from sky_events.apps.station.models import Station
from sky_events.apps.users.models import UserRole

from .models import Camera


class CameraForm(forms.ModelForm):

    class Meta:
        model = Camera
        fields = [
            "station",
            "name",
            "code",
            "detector",
            "camera_type",
            "model_name",
            "sensor_type",
            "resolution_width",
            "resolution_height",
            "fps",
            "field_of_view_deg",
            "lens_mm",
            "azimuth_deg",
            "elevation_deg",
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
