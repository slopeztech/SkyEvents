"""
Views for the reports app.

All write operations require admin role.
List / detail are accessible to authenticated users.

@file   sky_events/apps/reports/views.py
@author slopez.tech
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, ListView, View
from django.views.generic.edit import CreateView, UpdateView

from sky_events.apps.camera.models import Camera
from sky_events.apps.radio.models import RadioReceiver
from sky_events.apps.station.models import Station
from sky_events.apps.users.models import UserRole

from .forms import ReportFileFormSet, StationReportForm
from .models import ReportFile, ReportStatus, StationReport


class AdminRequiredMixin(LoginRequiredMixin):
    """Restrict access to admin users only."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != UserRole.ADMIN:
            messages.error(request, _("You do not have permission to access this page."))
            return redirect("web:dashboard")
        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


class ReportListView(LoginRequiredMixin, ListView):
    model = StationReport
    template_name = "pages/reports/list.html"
    context_object_name = "reports"
    paginate_by = 25

    def get_queryset(self):
        qs = StationReport.objects.select_related(
            "event", "station", "camera", "radio_receiver"
        ).order_by("-recorded_at")

        q = self.request.GET.get("q", "").strip()
        station_pk = self.request.GET.get("station", "")
        status = self.request.GET.get("status", "")

        if q:
            qs = qs.filter(station__name__icontains=q)
        if station_pk:
            qs = qs.filter(station_id=station_pk)
        if status:
            qs = qs.filter(status=status)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["station_filter"] = self.request.GET.get("station", "")
        ctx["status_filter"] = self.request.GET.get("status", "")
        ctx["station_list"] = Station.objects.order_by("name")
        ctx["status_choices"] = ReportStatus.choices
        return ctx


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


class ReportDetailView(LoginRequiredMixin, DetailView):
    model = StationReport
    template_name = "pages/reports/detail.html"
    context_object_name = "report"

    def get_queryset(self):
        return StationReport.objects.select_related(
            "event", "station", "camera__station", "radio_receiver__station"
        ).prefetch_related("files")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["file_formset"] = ReportFileFormSet(instance=self.object)
        return ctx


# ---------------------------------------------------------------------------
# Create / Edit
# ---------------------------------------------------------------------------


class ReportCreateView(AdminRequiredMixin, CreateView):
    model = StationReport
    form_class = StationReportForm
    template_name = "pages/reports/form.html"

    def get_success_url(self):
        return reverse_lazy("reports:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Report created successfully."))
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("New report")
        ctx["submit_label"] = _("Create report")
        return ctx


class ReportUpdateView(AdminRequiredMixin, UpdateView):
    model = StationReport
    form_class = StationReportForm
    template_name = "pages/reports/form.html"

    def get_success_url(self):
        return reverse_lazy("reports:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Report updated successfully."))
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("Edit report")
        ctx["submit_label"] = _("Save changes")
        return ctx


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class ReportDeleteView(AdminRequiredMixin, DeleteView):
    model = StationReport
    template_name = "pages/reports/confirm_delete.html"
    success_url = reverse_lazy("reports:list")
    context_object_name = "report"

    def form_valid(self, form):
        messages.success(self.request, _("Report deleted."))
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# File management (inline, via detail page)
# ---------------------------------------------------------------------------


class ReportFileAddView(AdminRequiredMixin, View):
    """Handle the inline file-add formset submitted from the detail page."""

    def post(self, request, pk):
        report = get_object_or_404(StationReport, pk=pk)
        formset = ReportFileFormSet(request.POST, instance=report)
        if formset.is_valid():
            formset.save()
            messages.success(request, _("Files updated."))
        else:
            for form in formset:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        return redirect("reports:detail", pk=pk)


class ReportFileDeleteView(AdminRequiredMixin, View):
    """Delete a single ReportFile."""

    def post(self, request, pk, file_pk):
        report_file = get_object_or_404(ReportFile, pk=file_pk, report_id=pk)
        report_file.delete()
        messages.success(request, _("File removed."))
        return redirect("reports:detail", pk=pk)
