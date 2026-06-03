"""
URL configuration for the reports app.

@file   sky_events/apps/reports/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportListView.as_view(), name="list"),
    path("new/", views.ReportCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.ReportDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.ReportUpdateView.as_view(), name="edit"),
    path("<uuid:pk>/delete/", views.ReportDeleteView.as_view(), name="delete"),
    # File sub-resources
    path("<uuid:pk>/files/", views.ReportFileAddView.as_view(), name="file_add"),
    path("<uuid:pk>/files/<uuid:file_pk>/delete/", views.ReportFileDeleteView.as_view(), name="file_delete"),
    path("<uuid:pk>/files/<uuid:file_pk>/request/", views.ReportFileRequestView.as_view(), name="file_request"),
    path(
        "<uuid:pk>/files/<uuid:file_pk>/attachments/<uuid:att_pk>/delete/",
        views.ReportAttachmentDeleteView.as_view(),
        name="attachment_delete",
    ),
]
