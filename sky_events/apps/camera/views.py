"""
Dashboard CRUD views for the camera app.  All views require admin role.

@file   sky_events/apps/camera/views.py
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

from .forms import CameraForm
from .models import Camera


class CameraRequiredMixin(LoginRequiredMixin):
    """Allow admins and station owners to manage their own cameras."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _("You do not have permission to access this page."))
            return redirect("web:dashboard")
        return super().dispatch(request, *args, **kwargs)


class CameraListView(CameraRequiredMixin, ListView):
    model = Camera
    template_name = "pages/cameras/list.html"
    context_object_name = "cameras"
    paginate_by = 25

    def get_queryset(self):
        qs = Camera.objects.select_related("station").order_by("station__name", "name")
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


class CameraDetailView(CameraRequiredMixin, DetailView):
    model = Camera
    template_name = "pages/cameras/detail.html"
    context_object_name = "camera"
    slug_field = "code"
    slug_url_kwarg = "code"

    def get_queryset(self):
        qs = Camera.objects.select_related("station")
        if self.request.user.role != UserRole.ADMIN:
            qs = qs.filter(station__owner=self.request.user)
        return qs


class CameraCreateView(CameraRequiredMixin, CreateView):
    model = Camera
    form_class = CameraForm
    template_name = "pages/cameras/form.html"
    success_url = reverse_lazy("camera:list")

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
        ctx["page_title"] = _("New camera")
        ctx["submit_label"] = _("Create camera")
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Camera created successfully."))
        return response


class CameraUpdateView(CameraRequiredMixin, UpdateView):
    model = Camera
    form_class = CameraForm
    template_name = "pages/cameras/form.html"
    slug_field = "code"
    slug_url_kwarg = "code"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("Edit camera")
        ctx["submit_label"] = _("Save changes")
        ctx["is_edit"] = True
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Camera updated successfully."))
        return response

    def get_success_url(self):
        return reverse_lazy("camera:detail", kwargs={"code": self.object.code})


class CameraDeleteView(CameraRequiredMixin, DeleteView):
    model = Camera
    template_name = "pages/cameras/confirm_delete.html"
    slug_field = "code"
    slug_url_kwarg = "code"
    success_url = reverse_lazy("camera:list")
    context_object_name = "camera"

    def form_valid(self, form):
        messages.success(self.request, _("Camera deleted."))
        return super().form_valid(form)
