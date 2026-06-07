from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from tests.factories import AdminUserFactory


@pytest.mark.django_db
class TestEventCards:
    def test_events_list_uses_collapsible_cards(self, client: Client) -> None:
        user = AdminUserFactory()
        user.save()
        client.force_login(user)

        response = client.get(reverse("events:list"))

        assert response.status_code == 200
        assert 'event-card-toggle' in response.content.decode("utf-8")
        assert 'event-card-body' in response.content.decode("utf-8")
