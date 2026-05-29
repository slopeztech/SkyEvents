"""
Dashboard CRUD views for the station app.  All views require admin role.

@file   sky_events/apps/station/views.py
@author slopez.tech
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from sky_events.apps.core.models import DeviceStatus
from sky_events.apps.users.models import UserRole

from .forms import StationForm
from .models import Station


class AdminRequiredMixin(LoginRequiredMixin):
    """Restrict access to admin users only."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != UserRole.ADMIN:
            messages.error(request, _("You do not have permission to access this page."))
            return redirect("web:dashboard")
        return super().dispatch(request, *args, **kwargs)


class StationListView(AdminRequiredMixin, ListView):
    model = Station
    template_name = "pages/stations/list.html"
    context_object_name = "stations"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Station.objects.select_related("owner")
            .annotate(
                cam_count=Count("cameras", distinct=True),
                radio_count=Count("radio_receivers", distinct=True),
            )
            .order_by("name")
        )
        if status := self.request.GET.get("status", ""):
            qs = qs.filter(status=status)
        if q := self.request.GET.get("q", ""):
            qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_filter"] = self.request.GET.get("status", "")
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_choices"] = DeviceStatus.choices
        return ctx


class StationDetailView(AdminRequiredMixin, DetailView):
    model = Station
    template_name = "pages/stations/detail.html"
    context_object_name = "station"
    slug_field = "code"
    slug_url_kwarg = "code"

    def get_queryset(self):
        return Station.objects.select_related("owner").prefetch_related(
            "cameras", "radio_receivers"
        )


class StationCreateView(AdminRequiredMixin, CreateView):
    model = Station
    form_class = StationForm
    template_name = "pages/stations/form.html"
    success_url = reverse_lazy("station:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("New station")
        ctx["submit_label"] = _("Create station")
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Station created successfully."))
        return response


class StationUpdateView(AdminRequiredMixin, UpdateView):
    model = Station
    form_class = StationForm
    template_name = "pages/stations/form.html"
    slug_field = "code"
    slug_url_kwarg = "code"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("Edit station")
        ctx["submit_label"] = _("Save changes")
        ctx["is_edit"] = True
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Station updated successfully."))
        return response

    def get_success_url(self):
        return reverse_lazy("station:detail", kwargs={"code": self.object.code})


class StationDeleteView(AdminRequiredMixin, DeleteView):
    model = Station
    template_name = "pages/stations/confirm_delete.html"
    slug_field = "code"
    slug_url_kwarg = "code"
    success_url = reverse_lazy("station:list")
    context_object_name = "station"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["camera_count"] = self.object.cameras.count()
        ctx["radio_count"] = self.object.radio_receivers.count()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, _("Station deleted."))
        return super().form_valid(form)
