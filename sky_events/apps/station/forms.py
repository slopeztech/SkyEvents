"""
Forms for the station app (admin dashboard usage).

@file   sky_events/apps/station/forms.py
@author slopez.tech
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from sky_events.apps.users.models import User, UserRole

from .models import Station


class StationForm(forms.ModelForm):

    class Meta:
        model = Station
        fields = [
            "owner",
            "name",
            "code",
            "description",
            "latitude",
            "longitude",
            "altitude_m",
            "timezone",
            "status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if self.request and self.request.user.role == UserRole.STATION_OWNER:
            self.fields["owner"].queryset = User.objects.filter(pk=self.request.user.pk)
            self.fields["owner"].initial = self.request.user.pk
            self.fields["owner"].disabled = True
        else:
            self.fields["owner"].queryset = User.objects.filter(is_active=True).order_by("email")
        self.fields["owner"].label_from_instance = lambda u: (
            f"{u.get_full_name()} <{u.email}>" if u.get_full_name() != u.email else u.email
        )
