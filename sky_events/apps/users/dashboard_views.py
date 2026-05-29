"""
Dashboard CRUD views for user management (admin only).

@file   sky_events/apps/users/dashboard_views.py
@author slopez.tech
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, View
from django.views.generic.edit import CreateView, UpdateView

from .dashboard_forms import UserCreateForm, UserEditForm
from .models import User, UserRole


class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != UserRole.ADMIN:
            messages.error(request, _("You do not have permission to access this page."))
            return redirect("web:dashboard")
        return super().dispatch(request, *args, **kwargs)


class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "pages/accounts/list.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        qs = User.objects.annotate(
            station_count=Count("stations", distinct=True),
        ).order_by("email")
        if role := self.request.GET.get("role", ""):
            qs = qs.filter(role=role)
        active = self.request.GET.get("active", "")
        if active == "1":
            qs = qs.filter(is_active=True)
        elif active == "0":
            qs = qs.filter(is_active=False)
        if q := self.request.GET.get("q", ""):
            qs = qs.filter(email__icontains=q) | qs.filter(username__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["role_filter"] = self.request.GET.get("role", "")
        ctx["active_filter"] = self.request.GET.get("active", "")
        ctx["q"] = self.request.GET.get("q", "")
        ctx["role_choices"] = UserRole.choices
        return ctx


class UserDetailView(AdminRequiredMixin, DetailView):
    model = User
    template_name = "pages/accounts/detail.html"
    context_object_name = "account"

    def get_queryset(self):
        return User.objects.prefetch_related("stations")


class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "pages/accounts/form.html"
    success_url = reverse_lazy("accounts:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("New user")
        ctx["submit_label"] = _("Create user")
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("User created successfully."))
        return response


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = UserEditForm
    template_name = "pages/accounts/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("Edit user")
        ctx["submit_label"] = _("Save changes")
        ctx["is_edit"] = True
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("User updated successfully."))
        return response

    def get_success_url(self):
        return reverse_lazy("accounts:detail", kwargs={"pk": self.object.pk})


class UserToggleActiveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, _("You cannot deactivate your own account."))
        else:
            user.is_active = not user.is_active
            user.save(update_fields=["is_active"])
            verb = _("activated") if user.is_active else _("deactivated")
            messages.success(
                request,
                _("User %(email)s %(verb)s.") % {"email": user.email, "verb": verb},
            )
        return redirect("accounts:detail", pk=pk)


class ScriptDataView(AdminRequiredMixin, DetailView):
    """
    Renders (or downloads) the script configuration file for a user.

    GET  /accounts/<pk>/script-data/           → HTML preview page
    GET  /accounts/<pk>/script-data/?format=json → JSON file download
    """

    model = User
    template_name = "pages/accounts/script_data.html"
    context_object_name = "account"

    def get_queryset(self):
        return User.objects.prefetch_related(
            "stations__cameras",
            "stations__radio_receivers",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_script_data(self, user: User) -> dict:
        """Build the JSON-serialisable dict that is written to the config file."""
        stations_data = []
        for station in user.stations.all().order_by("name"):
            stations_data.append(
                {
                    "hash_id": station.hash_id,
                    "name": station.name,
                    "code": station.code,
                    "cameras": [
                        {
                            "hash_id": cam.hash_id,
                            "name": cam.name,
                            "code": cam.code,
                        }
                        for cam in station.cameras.all().order_by("name")
                    ],
                    "radios": [
                        {
                            "hash_id": rdo.hash_id,
                            "name": rdo.name,
                            "code": rdo.code,
                        }
                        for rdo in station.radio_receivers.all().order_by("name")
                    ],
                }
            )
        return {
            "skyevents_version": "1.0",
            "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "user_token": user.script_token,
            "stations": stations_data,
        }

    # ------------------------------------------------------------------
    # Request handling
    # ------------------------------------------------------------------

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if request.GET.get("format") == "json":
            data = self._build_script_data(self.object)
            payload = json.dumps(data, indent=2, ensure_ascii=False)
            filename = f"skyevents_{self.object.username}_config.json"
            response = HttpResponse(payload, content_type="application/json")
            # ASCII-safe filename for broad browser compatibility
            safe_name = filename.encode("ascii", errors="replace").decode("ascii")
            response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
            return response

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        data = self._build_script_data(self.object)
        ctx["script_data_json"] = json.dumps(data, indent=2, ensure_ascii=False)
        ctx["script_data"] = data
        ctx["cameras_total"] = sum(len(s["cameras"]) for s in data["stations"])
        ctx["radios_total"] = sum(len(s["radios"]) for s in data["stations"])
        return ctx
