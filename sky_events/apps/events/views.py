"""
Views for the events app.

All write operations require admin role.
The list and detail views are accessible to authenticated users.

@file   sky_events/apps/events/views.py
@author slopez.tech
"""

from __future__ import annotations

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, View
from django.views.generic.edit import CreateView, UpdateView

from sky_events.apps.users.models import UserRole
from sky_events.apps.reports.models import StationReport

from .forms import AstronomicalEventForm
from .models import AstronomicalEvent, EventStatus


class AdminRequiredMixin(LoginRequiredMixin):
    """Restrict access to admin users only."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != UserRole.ADMIN:
            messages.error(request, _("You do not have permission to access this page."))
            return redirect("web:dashboard")
        return super().dispatch(request, *args, **kwargs)


class EventListView(LoginRequiredMixin, ListView):
    model = AstronomicalEvent
    template_name = "pages/events/list.html"
    context_object_name = "events"
    paginate_by = 20

    def get_queryset(self):
        reports_qs = (
            StationReport.objects.select_related("station", "camera", "radio_receiver")
            .annotate(files_count=Count("files"))
            .order_by("-recorded_at")
        )
        qs = (
            AstronomicalEvent.objects.select_related("created_by")
            .prefetch_related("stations", Prefetch("reports", queryset=reports_qs, to_attr="report_cards"))
            .order_by("-detected_at")
        )
        status = self.request.GET.get("status")
        event_type = self.request.GET.get("type")
        if status:
            qs = qs.filter(status=status)
        if event_type:
            qs = qs.filter(event_type=event_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = EventStatus.choices
        ctx["type_choices"] = AstronomicalEvent.event_type.field.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_type"] = self.request.GET.get("type", "")
        return ctx


class EventDetailView(LoginRequiredMixin, DetailView):
    model = AstronomicalEvent
    template_name = "pages/events/detail.html"
    context_object_name = "event"
    slug_field = "code"
    slug_url_kwarg = "code"

    def get_queryset(self):
        return AstronomicalEvent.objects.select_related("created_by").prefetch_related(
            "stations__owner", "cameras__station", "radio_receivers__station"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reports_qs = (
            self.object.reports
            .select_related("station", "camera", "radio_receiver")
            .annotate(files_count=Count("files"))
            .order_by("recorded_at")
        )
        stations_map: dict = {}
        for report in reports_qs:
            sid = str(report.station_id)
            if sid not in stations_map:
                s = report.station
                stations_map[sid] = {
                    "name": s.name,
                    "code": s.code,
                    "lat": float(s.latitude),
                    "lng": float(s.longitude),
                    "reports": [],
                }
            device = ""
            if report.camera:
                device = report.camera.name
            elif report.radio_receiver:
                device = report.radio_receiver.name
            stations_map[sid]["reports"].append({
                "pk": str(report.pk),
                "url": reverse("reports:detail", args=[str(report.pk)]),
                "recorded_at": report.recorded_at.strftime("%Y-%m-%d %H:%M:%S"),
                "device": device,
                "status": report.get_status_display(),
                "files": report.files_count,
            })
        ctx["map_stations_json"] = json.dumps(list(stations_map.values()))
        ctx["map_center_lat"] = getattr(settings, "MAP_DEFAULT_LAT", 40.4)
        ctx["map_center_lng"] = getattr(settings, "MAP_DEFAULT_LNG", -3.7)
        ctx["map_default_zoom"] = getattr(settings, "MAP_DEFAULT_ZOOM", 6)
        return ctx


class EventCreateView(AdminRequiredMixin, CreateView):
    model = AstronomicalEvent
    form_class = AstronomicalEventForm
    template_name = "pages/events/form.html"

    def _get_prefill_reports(self):
        if self.request.method == "POST":
            pks_str = self.request.POST.get("prefill_report_pks", "")
        else:
            pks_str = self.request.GET.get("reports", "")
        pks = [pk.strip() for pk in pks_str.split(",") if pk.strip()]
        if not pks:
            return StationReport.objects.none()
        return (
            StationReport.objects.filter(pk__in=pks, event__isnull=True)
            .select_related("station", "camera", "radio_receiver")
            .order_by("recorded_at")
        )

    def get_initial(self):
        initial = super().get_initial()
        reports = self._get_prefill_reports()
        if reports.exists():
            initial["detected_at"] = reports.first().recorded_at
            station_pks = list(
                reports.filter(station__isnull=False)
                .values_list("station_id", flat=True)
                .distinct()
            )
            camera_pks = list(
                reports.filter(camera__isnull=False)
                .values_list("camera_id", flat=True)
                .distinct()
            )
            radio_pks = list(
                reports.filter(radio_receiver__isnull=False)
                .values_list("radio_receiver_id", flat=True)
                .distinct()
            )
            if station_pks:
                initial["stations"] = station_pks
            if camera_pks:
                initial["cameras"] = camera_pks
            if radio_pks:
                initial["radio_receivers"] = radio_pks
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        pks_str = self.request.POST.get("prefill_report_pks", "")
        pks = [pk.strip() for pk in pks_str.split(",") if pk.strip()]
        if pks:
            StationReport.objects.filter(pk__in=pks, event__isnull=True).update(event=self.object)
        messages.success(self.request, _("Event %(code)s created successfully.") % {"code": self.object.code})
        return response

    def get_success_url(self):
        return reverse_lazy("events:detail", kwargs={"code": self.object.code})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("New event")
        ctx["submit_label"] = _("Create event")
        prefill = self._get_prefill_reports()
        if prefill.exists():
            ctx["prefill_reports"] = list(prefill)
            ctx["prefill_report_pks"] = ",".join(str(r.pk) for r in prefill)
        return ctx


class EventUpdateView(AdminRequiredMixin, UpdateView):
    model = AstronomicalEvent
    form_class = AstronomicalEventForm
    template_name = "pages/events/form.html"
    slug_field = "code"
    slug_url_kwarg = "code"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Event %(code)s updated.") % {"code": self.object.code})
        return response

    def get_success_url(self):
        return reverse_lazy("events:detail", kwargs={"code": self.object.code})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("Edit event — %(code)s") % {"code": self.object.code}
        ctx["submit_label"] = _("Save changes")
        return ctx


class EventPublishView(AdminRequiredMixin, View):
    """Toggle publish/unpublish via POST."""

    def post(self, request, code):
        event = get_object_or_404(AstronomicalEvent, code=code)
        if event.status == EventStatus.PUBLISHED:
            event.status = EventStatus.CONFIRMED
            messages.info(request, _("Event %(code)s unpublished.") % {"code": code})
        else:
            event.status = EventStatus.PUBLISHED
            messages.success(request, _("Event %(code)s published.") % {"code": code})
        event.save(update_fields=["status", "updated_at"])
        return redirect("events:detail", code=code)
