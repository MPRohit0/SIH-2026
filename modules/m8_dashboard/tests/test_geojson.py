"""Smoke tests for the mock JSON data used by the dashboard."""

from modules.m8_dashboard.services.api_client import get_mock_route_map


def test_mock_route_map_contains_expected_endpoints():
    route_map = get_mock_route_map()

    assert "POST /scenarios/resolve (slider)" in route_map
    assert "GET /flood?scenario_id=demo_dam_s60_froehlich_v1&models=sph,delft3d" in route_map
    assert "GET /impact?..." in route_map
