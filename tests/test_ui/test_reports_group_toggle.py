from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from tests.factories import AdminUserFactory


@pytest.mark.django_db
class TestReportsGroupToggle:
    def test_reports_page_initializes_group_resize_logic_for_expanded_tables(self) -> None:
        user = AdminUserFactory()
        user.save()

        client = Client()
        client.force_login(user)

        response = client.get(reverse("reports:list"))

        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "group-toggle" in html
        assert "sizeColumnsToFit" in html
