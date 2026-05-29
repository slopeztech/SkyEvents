"""
Dashboard forms for user management (admin only).

@file   sky_events/apps/users/dashboard_forms.py
@author slopez.tech
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import User


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        min_length=8,
    )
    password2 = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "first_name",
            "last_name",
            "organisation",
            "country",
            "timezone",
            "role",
        ]

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("Passwords do not match."))
        return p2

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "first_name",
            "last_name",
            "organisation",
            "country",
            "timezone",
            "role",
            "is_active",
        ]
