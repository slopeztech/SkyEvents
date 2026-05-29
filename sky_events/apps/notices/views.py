"""
Views for the notices app.

@file   sky_events/apps/notices/views.py
@author slopez.tech
"""

from __future__ import annotations

from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import FormView

from .forms import EventNoticeForm


class SubmitNoticeView(FormView):
    """
    Accepts POST submissions from the public event-notice form on the homepage.

    On success redirects back to the homepage (anchor #report) with a
    success message.  On failure redirects back with form errors stored in
    the session via Django messages.
    """

    form_class = EventNoticeForm
    success_url = reverse_lazy("web:index")

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            _("Thank you! Your report has been received and will be reviewed shortly."),
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                label = form.fields[field].label if field in form.fields else field
                messages.error(self.request, f"{label}: {error}")
        return self.form_invalid_redirect()

    def form_invalid_redirect(self):
        from django.shortcuts import redirect

        return redirect(reverse_lazy("web:index") + "#report")

    def get(self, request, *args, **kwargs):
        """GET not allowed — redirect to homepage."""
        from django.shortcuts import redirect

        return redirect("web:index")
