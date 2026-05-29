from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sky_events.apps.web"
    verbose_name = _("Web")
