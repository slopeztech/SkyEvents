from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from sky_events.apps.notices.forms import EventNoticeForm
from sky_events.apps.users.models import User, UserRole

from .forms import LoginForm

import json
import shutil


class IndexView(TemplateView):
    template_name = "pages/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["notice_form"] = EventNoticeForm()

        from sky_events.apps.events.models import AstronomicalEvent, EventStatus

        ctx["recent_events"] = (
            AstronomicalEvent.objects.filter(status=EventStatus.PUBLISHED)
            .order_by("-detected_at")
            .only("code", "name", "event_type", "detected_at")[:5]
        )
        return ctx


class LoginView(auth_views.LoginView):
    template_name = "pages/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("web:dashboard")


class LogoutView(auth_views.LogoutView):
    next_page = "web:index"


class DashboardView(LoginRequiredMixin, TemplateView):
    login_url = "/login/"

    def get_template_names(self):
        if self.request.user.role == UserRole.ADMIN:
            return ["pages/dashboard/admin_home.html"]
        return ["pages/dashboard/owner_home.html"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        from sky_events.apps.camera.models import Camera
        from sky_events.apps.core.models import DeviceStatus
        from sky_events.apps.radio.models import RadioReceiver
        from sky_events.apps.station.models import Station

        if user.role == UserRole.ADMIN:
            ctx["station_count"] = Station.objects.count()
            ctx["camera_count"] = Camera.objects.count()
            ctx["radio_count"] = RadioReceiver.objects.count()
            ctx["user_count"] = User.objects.count()
            ctx["owner_count"] = User.objects.filter(
                role=UserRole.STATION_OWNER
            ).count()

            ctx["station_active"] = Station.objects.filter(
                status=DeviceStatus.ACTIVE
            ).count()
            ctx["station_inactive"] = Station.objects.filter(
                status=DeviceStatus.INACTIVE
            ).count()
            ctx["station_maintenance"] = Station.objects.filter(
                status=DeviceStatus.MAINTENANCE
            ).count()

            ctx["recent_stations"] = (
                Station.objects.select_related("owner")
                .annotate(
                    cam_count=Count("cameras", distinct=True),
                    radio_count=Count("radio_receivers", distinct=True),
                )
                .order_by("-created_at")[:8]
            )

            # --- Stations map (with ping status) ---
            from django.conf import settings as django_settings
            from django.urls import reverse
            ping_threshold = timezone.now() - timezone.timedelta(seconds=60)
            all_stations = Station.objects.filter(
                latitude__isnull=False, longitude__isnull=False
            ).only("id", "name", "code", "latitude", "longitude", "last_ping_at", "status")
            map_stations = []
            for st in all_stations:
                is_online = (
                    st.last_ping_at is not None and st.last_ping_at >= ping_threshold
                )
                map_stations.append({
                    "name": st.name,
                    "code": st.code,
                    "lat": float(st.latitude),
                    "lng": float(st.longitude),
                    "online": is_online,
                    "last_ping": st.last_ping_at.isoformat() if st.last_ping_at else None,
                    "url": reverse("station:detail", kwargs={"code": st.code}),
                })
            ctx["map_stations_json"] = json.dumps(map_stations)
            ctx["map_center_lat"] = getattr(django_settings, "MAP_DEFAULT_LAT", 40.4)
            ctx["map_center_lng"] = getattr(django_settings, "MAP_DEFAULT_LNG", -3.7)
            ctx["map_center_zoom"] = getattr(django_settings, "MAP_DEFAULT_ZOOM", 6)

            # --- Recent reports ---
            from sky_events.apps.reports.models import StationReport
            ctx["recent_reports"] = (
                StationReport.objects.select_related("station", "camera", "radio_receiver")
                .order_by("-created_at")[:10]
            )

            # --- Recent events ---
            from sky_events.apps.events.models import AstronomicalEvent
            ctx["recent_events"] = (
                AstronomicalEvent.objects.order_by("-detected_at")[:10]
            )

            # --- System stats ---
            try:
                import psutil
                cpu_pct = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                ctx["sys_cpu_pct"] = round(cpu_pct, 1)
                ctx["sys_mem_total_gb"] = round(mem.total / 1024**3, 1)
                ctx["sys_mem_used_gb"] = round(mem.used / 1024**3, 1)
                ctx["sys_mem_pct"] = mem.percent
            except ImportError:
                ctx["sys_cpu_pct"] = None
                ctx["sys_mem_pct"] = None

            try:
                import django
                from pathlib import Path
                base_dir = Path(django_settings.BASE_DIR)
                disk = shutil.disk_usage(str(base_dir))
                ctx["sys_disk_total_gb"] = round(disk.total / 1024**3, 1)
                ctx["sys_disk_used_gb"] = round(disk.used / 1024**3, 1)
                ctx["sys_disk_free_gb"] = round(disk.free / 1024**3, 1)
                ctx["sys_disk_pct"] = round(disk.used / disk.total * 100, 1)
            except Exception:
                ctx["sys_disk_pct"] = None

            week_ago = timezone.now() - timezone.timedelta(days=7)
            recent_users = User.objects.filter(created_at__gte=week_ago).count()

            notices = []
            if ctx["station_inactive"]:
                n = ctx["station_inactive"]
                notices.append(
                    {
                        "level": "error",
                        "icon": "offline",
                        "title": f"{n} estación{'es' if n != 1 else ''} offline",
                        "desc": "Requieren revisión inmediata.",
                    }
                )
            if ctx["station_maintenance"]:
                n = ctx["station_maintenance"]
                notices.append(
                    {
                        "level": "warning",
                        "icon": "maintenance",
                        "title": f"{n} estación{'es' if n != 1 else ''} en mantenimiento",
                        "desc": "Actualiza el estado cuando se resuelvan.",
                    }
                )
            if recent_users:
                notices.append(
                    {
                        "level": "info",
                        "icon": "users",
                        "title": f"{recent_users} usuario{'s' if recent_users != 1 else ''} nuevo{'s' if recent_users != 1 else ''} esta semana",
                        "desc": "Revisa y asigna roles según corresponda.",
                    }
                )
            if not notices:
                notices.append(
                    {
                        "level": "success",
                        "icon": "check",
                        "title": "Red saludable",
                        "desc": "Todas las estaciones activas, sin incidencias.",
                    }
                )
            ctx["notices"] = notices

        else:
            ctx["my_station_count"] = Station.objects.filter(owner=user).count()
            ctx["my_camera_count"] = Camera.objects.filter(station__owner=user).count()
            ctx["my_radio_count"] = RadioReceiver.objects.filter(
                station__owner=user
            ).count()

        return ctx
