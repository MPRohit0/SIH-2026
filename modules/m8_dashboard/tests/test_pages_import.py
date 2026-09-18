"""Smoke tests for the dashboard skeleton imports."""

import importlib.util


def test_component_imports():
    import modules.m8_dashboard.components.map as map_component
    import modules.m8_dashboard.components.metrics as metrics_component
    import modules.m8_dashboard.components.site_form as site_form_component
    import modules.m8_dashboard.services.api_client as api_client

    assert hasattr(map_component, "render_site_map")
    assert hasattr(metrics_component, "render_metric_cards")
    assert hasattr(site_form_component, "render_site_form")
    assert hasattr(api_client, "get_flood_response")


def test_page_scripts_are_loadable():
    for page_path in [
        "modules/m8_dashboard/pages/1_Home.py",
        "modules/m8_dashboard/pages/2_Add_Site.py",
        "modules/m8_dashboard/pages/3_Site_Dashboard.py",
    ]:
        spec = importlib.util.spec_from_file_location(page_path.replace("/", "_"), page_path)
        assert spec is not None and spec.loader is not None
