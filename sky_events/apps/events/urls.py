"""
URL configuration for the events app.

@file   sky_events/apps/events/urls.py
@author slopez.tech
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("events/", views.EventListView.as_view(), name="list"),
    path("events/new/", views.EventCreateView.as_view(), name="create"),
    path("events/<str:code>/", views.EventDetailView.as_view(), name="detail"),
    path("events/<str:code>/edit/", views.EventUpdateView.as_view(), name="edit"),
    path("events/<str:code>/publish/", views.EventPublishView.as_view(), name="publish"),
]
