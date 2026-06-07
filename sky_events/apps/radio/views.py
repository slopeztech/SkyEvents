"""
Dashboard CRUD views for the radio app.  All views require admin role.

@file   sky_events/apps/radio/views.py
@author slopez.tech
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from sky_events.apps.core.models import DeviceStatus
from sky_events.apps.station.models import Station
from sky_events.apps.users.models import UserRole

from .forms import RadioReceiverForm
from .models import RadioReceiver


class RadioRequiredMixin(LoginRequiredMixin):
    """Allow admins and station owners to manage their own radio receivers."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _("You do not have permission to access this page."))
            return redirect("web:dashboard")
        return super().dispatch(request, *args, **kwargs)


class RadioListView(RadioRequiredMixin, ListView):
    model = RadioReceiver
    template_name = "pages/radios/list.html"
    context_object_name = "radios"
    paginate_by = 25

    def get_queryset(self):
        qs = RadioReceiver.objects.select_related("station").order_by("station__name", "name")
        if self.request.user.role != UserRole.ADMIN:
            qs = qs.filter(station__owner=self.request.user)
        if status := self.request.GET.get("status", ""):
            qs = qs.filter(status=status)
        if station_code := self.request.GET.get("station", ""):
            qs = qs.filter(station__code=station_code)
        if q := self.request.GET.get("q", ""):
            qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_filter"] = self.request.GET.get("status", "")
        ctx["station_filter"] = self.request.GET.get("station", "")
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_choices"] = DeviceStatus.choices
        ctx["station_list"] = Station.objects.order_by("name").values("code", "name")
        return ctx


class RadioDetailView(RadioRequiredMixin, DetailView):
    model = RadioReceiver
    template_name = "pages/radios/detail.html"
    context_object_name = "radio"
    slug_field = "code"
    slug_url_kwarg = "code"

    def get_queryset(self):
        qs = RadioReceiver.objects.select_related("station")
        if self.request.user.role != UserRole.ADMIN:
            qs = qs.filter(station__owner=self.request.user)
        return qs


class RadioCreateView(RadioRequiredMixin, CreateView):
    model = RadioReceiver
    form_class = RadioReceiverForm
    template_name = "pages/radios/form.html"
    success_url = reverse_lazy("radio:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if station_code := self.request.GET.get("station", ""):
            try:
                initial["station"] = Station.objects.get(code=station_code)
            except Station.DoesNotExist:
                pass
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("New radio receiver")
        ctx["submit_label"] = _("Create radio receiver")
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Radio receiver created successfully."))
        return response


class RadioUpdateView(RadioRequiredMixin, UpdateView):
    model = RadioReceiver
    form_class = RadioReceiverForm
    template_name = "pages/radios/form.html"
    slug_field = "code"
    slug_url_kwarg = "code"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("Edit radio receiver")
        ctx["submit_label"] = _("Save changes")
        ctx["is_edit"] = True
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Radio receiver updated successfully."))
        return response

    def get_success_url(self):
        return reverse_lazy("radio:detail", kwargs={"code": self.object.code})


class RadioDeleteView(RadioRequiredMixin, DeleteView):
    model = RadioReceiver
    template_name = "pages/radios/confirm_delete.html"
    slug_field = "code"
    slug_url_kwarg = "code"
    success_url = reverse_lazy("radio:list")
    context_object_name = "radio"

    def form_valid(self, form):
        messages.success(self.request, _("Radio receiver deleted."))
        return super().form_valid(form)
