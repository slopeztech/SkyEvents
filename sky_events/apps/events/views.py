"""
Views for the events app.

All write operations require admin role.
The list and detail views are accessible to authenticated users.

@file   sky_events/apps/events/views.py
@author slopez.tech
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, View
from django.views.generic.edit import CreateView, UpdateView

from sky_events.apps.users.models import UserRole

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
        qs = (
            AstronomicalEvent.objects.select_related("created_by")
            .prefetch_related("stations")
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


class EventCreateView(AdminRequiredMixin, CreateView):
    model = AstronomicalEvent
    form_class = AstronomicalEventForm
    template_name = "pages/events/form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, _("Event %(code)s created successfully.") % {"code": self.object.code})
        return response

    def get_success_url(self):
        return reverse_lazy("events:detail", kwargs={"code": self.object.code})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("New event")
        ctx["submit_label"] = _("Create event")
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
