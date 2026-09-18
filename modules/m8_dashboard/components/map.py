"""Reusable Map Component for SIH26161 Module 8 Dashboard.

Creates Folium maps, renders river vector layers, manages polyline drawing,
and handles spatial bounding box auto-fitting.
"""

from __future__ import annotations

from typing import Any
import folium
from folium.plugins import Draw, Fullscreen
from streamlit_folium import st_folium

INDIA_CENTER = [20.5937, 78.9629]
DEFAULT_ZOOM = 5


def create_base_map(
    center: list[float] | tuple[float, float] = INDIA_CENTER,
    zoom: int = DEFAULT_ZOOM,
) -> folium.Map:
    """Create a clean base Folium map centered on India."""
    m = folium.Map(
        location=list(center),
        zoom_start=zoom,
        tiles="OpenStreetMap",
        control_scale=True,
    )
    Fullscreen(position="topright").add_to(m)
    return m


def compute_rivers_bounds(rivers: list[dict[str, Any]]) -> list[list[float]] | None:
    """Compute [[min_lat, min_lon], [max_lat, max_lon]] across all river coordinates."""
    lats: list[float] = []
    lons: list[float] = []

    for feature in rivers:
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [])
        for pt in coords:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                try:
                    lon, lat = float(pt[0]), float(pt[1])
                    lons.append(lon)
                    lats.append(lat)
                except (ValueError, TypeError):
                    continue

    if not lats or not lons:
        return None

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # If all points are identical, add a small buffer
    if min_lat == max_lat:
        min_lat -= 0.05
        max_lat += 0.05
    if min_lon == max_lon:
        min_lon -= 0.05
        max_lon += 0.05

    return [[min_lat, min_lon], [max_lat, max_lon]]


def add_rivers_to_map(
    folium_map: folium.Map,
    rivers: list[dict[str, Any]],
    highlight_id: str | None = None,
) -> folium.Map:
    """Render saved river features as styled GeoJson vector lines."""
    for feature in rivers:
        props = feature.get("properties", {})
        river_id = props.get("river_id", "unknown")
        river_name = props.get("river_name", "Unnamed River")
        source = props.get("source", "manual")
        created_at = props.get("created_at", "N/A")
        coords = feature.get("geometry", {}).get("coordinates", [])
        pt_count = len(coords)

        is_highlighted = highlight_id is not None and river_id == highlight_id
        color = "#E53935" if is_highlighted else "#1E88E5"
        weight = 6 if is_highlighted else 4
        opacity = 1.0 if is_highlighted else 0.85

        popup_html = f"""
        <div style="font-family: sans-serif; font-size: 13px; min-width: 180px;">
            <b style="color: {color}; font-size: 14px;">{river_name}</b><br/>
            <hr style="margin: 4px 0;"/>
            <b>ID:</b> <code>{river_id}</code><br/>
            <b>Source:</b> {source}<br/>
            <b>Points:</b> {pt_count}<br/>
            <b>Created:</b> {created_at[:10] if len(created_at) >= 10 else created_at}
        </div>
        """

        folium.GeoJson(
            feature,
            name=f"{river_name} ({river_id})",
            style_function=lambda _, c=color, w=weight, o=opacity: {
                "color": c,
                "weight": w,
                "opacity": o,
            },
            tooltip=folium.Tooltip(f"🌊 {river_name} ({river_id})"),
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(folium_map)

    return folium_map


def fit_map_to_rivers(
    folium_map: folium.Map,
    rivers: list[dict[str, Any]],
    highlight_id: str | None = None,
) -> folium.Map:
    """Auto-fit folium map viewport to rivers bounding box."""
    target_rivers = rivers
    if highlight_id:
        highlighted = [r for r in rivers if r.get("properties", {}).get("river_id") == highlight_id]
        if highlighted:
            target_rivers = highlighted

    bounds = compute_rivers_bounds(target_rivers)
    if bounds:
        folium_map.fit_bounds(bounds, padding=(30, 30))
    return folium_map


def extract_drawn_linestring(st_folium_output: dict[str, Any] | None) -> dict[str, Any] | None:
    """Extract a valid LineString geometry dictionary from streamlit-folium output."""
    if not st_folium_output or not isinstance(st_folium_output, dict):
        return None

    # Check last_active_drawing
    last = st_folium_output.get("last_active_drawing")
    if last and isinstance(last, dict):
        geom = last.get("geometry")
        if isinstance(geom, dict) and geom.get("type") == "LineString":
            coords = geom.get("coordinates", [])
            if isinstance(coords, list) and len(coords) >= 2:
                return geom

    # Check all_drawings list in reverse order
    all_drawings = st_folium_output.get("all_drawings")
    if isinstance(all_drawings, list):
        for item in reversed(all_drawings):
            if isinstance(item, dict):
                geom = item.get("geometry")
                if isinstance(geom, dict) and geom.get("type") == "LineString":
                    coords = geom.get("coordinates", [])
                    if isinstance(coords, list) and len(coords) >= 2:
                        return geom

    return None


def render_river_map(
    rivers: list[dict[str, Any]] | None = None,
    enable_drawing: bool = False,
    highlight_id: str | None = None,
    height: int = 500,
    center: list[float] | tuple[float, float] = INDIA_CENTER,
    zoom: int = DEFAULT_ZOOM,
    auto_fit: bool = True,
    key: str = "river_map",
) -> dict[str, Any] | None:
    """Build and render an interactive river map in Streamlit using streamlit-folium.

    Returns the output dictionary from st_folium.
    """
    m = create_base_map(center=center, zoom=zoom)

    river_list = rivers or []
    if river_list:
        add_rivers_to_map(m, river_list, highlight_id=highlight_id)
        if auto_fit:
            fit_map_to_rivers(m, river_list, highlight_id=highlight_id)

    if enable_drawing:
        Draw(
            export=False,
            position="topleft",
            draw_options={
                "polyline": {
                    "shapeOptions": {
                        "color": "#1E88E5",
                        "weight": 5,
                        "opacity": 0.9,
                    }
                },
                "polygon": False,
                "rectangle": False,
                "circle": False,
                "marker": False,
                "circlemarker": False,
            },
            edit_options={"edit": False, "remove": True},
        ).add_to(m)

    output = st_folium(
        m,
        height=height,
        use_container_width=True,
        key=key,
        returned_objects=["last_active_drawing", "all_drawings"] if enable_drawing else [],
    )
    return output
