"""
Django admin configuration for the users application.

@file   sky_events/apps/users/admin.py
@author slopez.tech
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from sky_events.apps.users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin configuration for the custom User model.

    Extends Django's built-in UserAdmin to support email-based auth
    and the custom fields added to SkyEvents' User model.
    """

    ordering = ["email"]
    list_display = [
        "email",
        "username",
        "get_full_name",
        "role",
        "is_active",
        "is_staff",
        "created_at",
    ]
    list_filter = ["is_active", "is_staff", "role", "country"]
    search_fields = ["email", "username", "first_name", "last_name", "organisation"]
    readonly_fields = ["id", "created_at", "updated_at", "last_login"]

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "organisation",
                    "country",
                    "timezone",
                )
            },
        ),
        (
            _("Roles & permissions"),
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Dates"),
            {
                "fields": ("last_login", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "role",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
