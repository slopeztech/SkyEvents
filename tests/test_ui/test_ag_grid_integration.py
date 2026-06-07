from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestAgGridIntegration:
    def test_base_template_loads_ag_grid_assets(self, client: Client) -> None:
        response = client.get(reverse("web:index"))

        assert response.status_code == 200
        assert "ag-grid-community.min.js" in response.content.decode("utf-8")
        assert "ag-grid-init.js" in response.content.decode("utf-8")
