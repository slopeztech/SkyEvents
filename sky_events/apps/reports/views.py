"""
Views for the reports app.

Manual report creation is available to authenticated users.
Edit / delete operations remain admin-only.

@file   sky_events/apps/reports/views.py
@author slopez.tech
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, ListView, View
from django.views.generic.edit import CreateView, UpdateView

from sky_events.apps.camera.models import Camera
from sky_events.apps.radio.models import RadioReceiver
from sky_events.apps.station.models import Station
from sky_events.apps.users.models import UserRole

from .forms import ReportFileFormSet, StationReportForm
from .models import MediaRequirement, ReportAttachment, ReportFile, ReportStatus, RequirementStatus, StationReport


class AdminRequiredMixin(LoginRequiredMixin):
    """Restrict access to admin users only."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != UserRole.ADMIN:
            messages.error(request, _("You do not have permission to access this page."))
            return redirect("web:dashboard")
        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# List — tabbed, time-grouped
# ---------------------------------------------------------------------------

REPORT_TABS = [
    ("latest", _("Latest 50")),
    ("today", _("Today")),
    ("yesterday", _("Yesterday")),
    ("7d", _("Last 7 days")),
    ("14d", _("Last 14 days")),
    ("31d", _("Last 31 days")),
]
_REPORT_TAB_KEYS = {t[0] for t in REPORT_TABS}
_GROUP_GAP_SECONDS = 30


def _make_group_meta(reports, *, kind="time", event=None):
    """Build metadata for a report group used by the UI."""
    station_names = list(dict.fromkeys(r.station.name for r in reports if r.station))
    ordered = list(reports)
    ordered.sort(key=lambda item: item.recorded_at, reverse=True)
    return {
        "kind": kind,
        "event": event,
        "reports": ordered,
        "count": len(ordered),
        "stations": station_names,
        "has_unlinked": any(r.event_id is None for r in ordered),
        # newest-first for display
        "time_end": ordered[0].recorded_at,
        "time_start": ordered[-1].recorded_at,
    }


def _build_time_groups(reports):
    """Group reports by temporal proximity when they are not linked to an event."""
    if not reports:
        return []

    groups = []
    current = [reports[0]]
    for rep in reports[1:]:
        gap = abs((current[-1].recorded_at - rep.recorded_at).total_seconds())
        if gap <= _GROUP_GAP_SECONDS:
            current.append(rep)
        else:
            groups.append(_make_group_meta(current, kind="time"))
            current = [rep]
    groups.append(_make_group_meta(current, kind="time"))
    return groups


def _build_report_groups(reports):
    """Group reports by event first, then by time proximity for the rest."""
    if not reports:
        return []

    groups = []
    event_map = {}
    for rep in reports:
        if rep.event_id:
            event_map.setdefault(rep.event_id, []).append(rep)

    for event_id, event_reports in event_map.items():
        event = event_reports[0].event
        groups.append(_make_group_meta(event_reports, kind="event", event=event))

    remaining = [rep for rep in reports if rep.event_id is None]
    groups.extend(_build_time_groups(remaining))
    return groups


class ReportListView(LoginRequiredMixin, View):
    template_name = "pages/reports/list.html"

    def get(self, request):
        tab = request.GET.get("tab", "latest")
        if tab not in _REPORT_TAB_KEYS:
            tab = "latest"

        now = timezone.now()
        today = now.date()

        base_qs = (
            StationReport.objects.select_related("event", "station", "camera", "radio_receiver")
            .annotate(files_count=Count("files"))
            .order_by("-recorded_at")
        )

        if tab == "latest":
            reports = list(base_qs[:50])
        elif tab == "today":
            reports = list(base_qs.filter(recorded_at__date=today))
        elif tab == "yesterday":
            reports = list(base_qs.filter(recorded_at__date=today - timedelta(days=1)))
        elif tab == "7d":
            reports = list(base_qs.filter(recorded_at__gte=now - timedelta(days=7)))
        elif tab == "14d":
            reports = list(base_qs.filter(recorded_at__gte=now - timedelta(days=14)))
        else:  # 31d
            reports = list(base_qs.filter(recorded_at__gte=now - timedelta(days=31)))

        groups = _build_report_groups(reports)

        return render(request, self.template_name, {
            "tabs": REPORT_TABS,
            "active_tab": tab,
            "groups": groups,
            "total": len(reports),
        })


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
        ).prefetch_related(
            "files__requirements__attachments",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["file_formset"] = ReportFileFormSet(instance=self.object)
        return ctx


# ---------------------------------------------------------------------------
# Create / Edit
# ---------------------------------------------------------------------------


class ReportCreateView(LoginRequiredMixin, CreateView):
    model = StationReport
    form_class = StationReportForm
    template_name = "pages/reports/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

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


# ---------------------------------------------------------------------------
# File request (creates a MediaRequirement for the station to upload the file)
# ---------------------------------------------------------------------------


class ReportFileRequestView(AdminRequiredMixin, View):
    """Create a MediaRequirement so the station uploads this file."""

    def post(self, request, pk, file_pk):
        report_file = get_object_or_404(ReportFile, pk=file_pk, report_id=pk)
        report = report_file.report

        # Avoid duplicate pending requirements for the same file.
        existing = report_file.requirements.filter(
            status=RequirementStatus.PENDING
        ).first()
        if not existing:
            MediaRequirement.objects.create(
                station=report.station,
                report_file=report_file,
                requested_by=request.user,
                requested_paths=[report_file.filename],
                notes=_("Requested from report #%(pk)s") % {"pk": str(report.pk)[:8]},
            )
            messages.success(request, _("Request sent to the station."))
        else:
            messages.info(request, _("A pending request already exists for this file."))

        return redirect("reports:detail", pk=pk)


# ---------------------------------------------------------------------------
# Attachment delete (removes the uploaded file from server)
# ---------------------------------------------------------------------------


class ReportAttachmentDeleteView(AdminRequiredMixin, View):
    """Delete only the physical file from storage; keep the DB record so it can be re-requested."""

    def post(self, request, pk, file_pk, att_pk):
        attachment = get_object_or_404(
            ReportAttachment,
            pk=att_pk,
            requirement__report_file_id=file_pk,
            requirement__report_file__report_id=pk,
        )
        # Delete the physical file from storage but keep the record.
        if attachment.file:
            attachment.file.delete(save=False)
            attachment.file = ""
            attachment.save(update_fields=["file"])
        messages.success(request, _("File deleted from server. The record is kept so it can be re-requested."))
        return redirect("reports:detail", pk=pk)
