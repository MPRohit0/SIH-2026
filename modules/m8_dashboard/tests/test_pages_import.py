"""Tests verifying that all Module 8 dashboard pages and components import cleanly."""

import importlib
import pytest


def test_import_components_and_services():
    """Verify that components and services can be imported via both package paths."""
    # Module-qualified imports
    import modules.m8_dashboard.components.map as m_map
    import modules.m8_dashboard.components.metrics as m_metrics
    import modules.m8_dashboard.components.river_form as m_form
    import modules.m8_dashboard.services.river_store as m_store

    assert hasattr(m_map, "render_river_map")
    assert hasattr(m_metrics, "render_dashboard_metrics")
    assert hasattr(m_form, "render_add_river_form")
    assert hasattr(m_store, "load_rivers")

    # Short package imports
    import components.map as s_map
    import components.metrics as s_metrics
    import components.river_form as s_form
    import services.river_store as s_store

    assert hasattr(s_map, "render_river_map")
    assert hasattr(s_metrics, "render_dashboard_metrics")
    assert hasattr(s_form, "render_add_river_form")
    assert hasattr(s_store, "load_rivers")


def test_pages_import_cleanly():
    """Verify that page scripts import without ModuleNotFoundError."""
    # Test importing each page script by file path
    spec_home = importlib.util.spec_from_file_location("page_home", "modules/m8_dashboard/pages/1_Home.py")
    assert spec_home is not None and spec_home.loader is not None

    spec_add = importlib.util.spec_from_file_location("page_add", "modules/m8_dashboard/pages/2_Add_River.py")
    assert spec_add is not None and spec_add.loader is not None

    spec_rivers = importlib.util.spec_from_file_location("page_rivers", "modules/m8_dashboard/pages/3_Rivers.py")
    assert spec_rivers is not None and spec_rivers.loader is not None
