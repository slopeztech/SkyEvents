"""
Views for the webconfig app.

Only accessible to admin users.

@file   sky_events/apps/webconfig/views.py
@author slopez.tech
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import UpdateView

from sky_events.apps.users.models import UserRole

from .forms import SiteConfigForm
from .models import SiteConfig

_SUPPORTED = [code for code, _name in settings.LANGUAGES]


class AdminRequiredMixin(LoginRequiredMixin):
    """Restrict access to admin users only."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != UserRole.ADMIN:
            messages.error(request, _("You do not have permission to access this page."))
            return redirect("web:dashboard")
        return super().dispatch(request, *args, **kwargs)


class WebConfigView(AdminRequiredMixin, UpdateView):
    """Edit the SiteConfig for a specific language (selected via ?lang=XX tab)."""

    model = SiteConfig
    form_class = SiteConfigForm
    template_name = "pages/webconfig/edit.html"

    def _get_lang(self) -> str:
        lang = self.request.POST.get("lang") or self.request.GET.get("lang", "")
        return lang if lang in _SUPPORTED else settings.LANGUAGE_CODE

    def get_object(self, queryset=None):  # noqa: ARG002
        return SiteConfig.load(self._get_lang())

    def get_success_url(self) -> str:
        return f"{reverse('webconfig:edit')}?lang={self._get_lang()}"

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Site configuration saved successfully."))
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = _("Web Configuration")
        ctx["current_lang"] = self._get_lang()
        ctx["languages"] = settings.LANGUAGES
        return ctx
