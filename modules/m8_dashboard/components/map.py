"""Local map components for site and flood-result visualization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import folium
from streamlit_folium import st_folium

REPO_ROOT = Path(__file__).resolve().parents[3]
MOCK_ARTIFACT_ROOT = REPO_ROOT / "data" / "mock" / "artifacts"


def _mock_artifact_path(url: str | None) -> Path | None:
    """Resolve a mock URL without exposing a filesystem path to the UI."""
    if not url or not url.startswith("/mock-api/artifacts/"):
        return None
    relative_path = url.removeprefix("/mock-api/artifacts/")
    candidate = (MOCK_ARTIFACT_ROOT / relative_path).resolve()
    if MOCK_ARTIFACT_ROOT not in candidate.parents:
        return None
    return candidate


def _read_geojson_artifact(artifact: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not artifact or artifact.get("kind") != "vector":
        return None
    path = _mock_artifact_path(artifact.get("url"))
    if path is None or not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _center_from_bbox(bbox: Sequence[float]) -> tuple[float, float]:
    return ((bbox[1] + bbox[3]) / 2.0, (bbox[0] + bbox[2]) / 2.0)


def render_site_map(bbox_wgs84: Sequence[float] | None = None) -> None:
    """Render a simple site context map."""
    bbox = bbox_wgs84 or [79.72, 30.5, 79.9, 30.65]
    latitude, longitude = _center_from_bbox(bbox)
    st.map([
        {"lat": latitude, "lon": longitude},
        {"lat": bbox[1], "lon": bbox[0]},
        {"lat": bbox[3], "lon": bbox[2]},
    ])


def render_flood_result_map(
    *,
    site_location: Mapping[str, float],
    site_bbox_wgs84: Sequence[float] | None,
    flood_result: Mapping[str, Any],
    height: int = 560,
) -> dict[str, Any] | None:
    """Render only geographic products supplied by a FloodQueryResponse."""
    bbox = site_bbox_wgs84 or [79.72, 30.5, 79.9, 30.65]
    center = _center_from_bbox(bbox)
    flood_map = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap")

    site_lat = site_location.get("lat")
    site_lon = site_location.get("lon")
    if site_lat is not None and site_lon is not None:
        folium.Marker(
            [site_lat, site_lon],
            tooltip="Failure source",
            popup=f"Failure location: {site_lon}, {site_lat}",
            icon=folium.Icon(color="red", icon="warning-sign"),
        ).add_to(flood_map)

    folium.Rectangle(
        bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
        tooltip="Site/domain bounding box",
        color="#555555",
        fill=False,
    ).add_to(flood_map)

    extent = _read_geojson_artifact(flood_result.get("max_extent"))
    if extent is not None:
        folium.GeoJson(
            extent,
            name="Simulated maximum flood extent",
            style_function=lambda _: {
                "color": "#1565c0",
                "fillColor": "#42a5f5",
                "fillOpacity": 0.35,
                "weight": 2,
            },
            tooltip="Simulated maximum flood extent",
        ).add_to(flood_map)

    depth = flood_result.get("timesteps", [{}])[-1].get("depth")
    max_depth = flood_result.get("max_depth_m")
    depth_label = f"Maximum flood depth: {max_depth} m" if max_depth is not None else "Maximum flood depth unavailable"
    if depth and depth.get("available"):
        folium.Marker(
            center,
            tooltip="Flood depth information",
            popup=f"{depth_label}<br>Raster artifact: {depth.get('artifact_id')}",
            icon=folium.Icon(color="blue", icon="tint"),
        ).add_to(flood_map)

    layers = {
        "Velocity raster": flood_result.get("timesteps", [{}])[-1].get("velocity"),
        "Arrival-time raster": flood_result.get("arrival_time"),
    }
    for label, artifact in layers.items():
        if artifact and artifact.get("available"):
            folium.Marker(
                center,
                tooltip=label,
                popup=f"{label}<br>Raster artifact: {artifact.get('artifact_id')}",
                icon=folium.Icon(color="cadetblue", icon="info-sign"),
            ).add_to(flood_map)

    folium.LayerControl().add_to(flood_map)
    return st_folium(flood_map, height=height, use_container_width=True)


def render_historical_validation_map(
    *,
    site_location: Mapping[str, float],
    site_bbox_wgs84: Sequence[float] | None,
    historical_result: Mapping[str, Any],
    flood_result: Mapping[str, Any] | None = None,
    height: int = 560,
) -> dict[str, Any] | None:
    """Render observed historical products and an available simulated extent."""
    bbox = site_bbox_wgs84 or [79.72, 30.5, 79.9, 30.65]
    validation_map = folium.Map(location=_center_from_bbox(bbox), zoom_start=11)

    site_lat = site_location.get("lat")
    site_lon = site_location.get("lon")
    if site_lat is not None and site_lon is not None:
        folium.Marker(
            [site_lat, site_lon],
            tooltip="Failure source",
            icon=folium.Icon(color="red", icon="warning-sign"),
        ).add_to(validation_map)

    observations = historical_result.get("observations", {})
    observed_extent = _read_geojson_artifact(observations.get("extent"))
    if observed_extent is not None:
        folium.GeoJson(
            observed_extent,
            name="Observed historical extent",
            style_function=lambda _: {
                "color": "#2e7d32",
                "fillColor": "#66bb6a",
                "fillOpacity": 0.35,
                "weight": 2,
            },
            tooltip="Observed historical extent",
        ).add_to(validation_map)

    if flood_result:
        simulated_extent = _read_geojson_artifact(flood_result.get("max_extent"))
        if simulated_extent is not None:
            folium.GeoJson(
                simulated_extent,
                name="Simulated flood extent",
                style_function=lambda _: {
                    "color": "#1565c0",
                    "fillColor": "#42a5f5",
                    "fillOpacity": 0.25,
                    "weight": 2,
                },
                tooltip="Simulated flood extent",
            ).add_to(validation_map)

    point_groups = (
        ("Observed arrival time", observations.get("arrival_time_points", []), "orange", "arrival_time_min"),
        ("Observed depth", observations.get("depth_points", []), "blue", "depth_m"),
        ("Observed velocity", observations.get("velocity_points", []), "purple", "velocity_ms"),
    )
    for label, points, color, value_key in point_groups:
        for point in points or []:
            location = point.get("location", {})
            if location.get("lat") is None or location.get("lon") is None:
                continue
            folium.CircleMarker(
                [location["lat"], location["lon"]],
                radius=5,
                color=color,
                fill=True,
                tooltip=label,
                popup=f"{label}: {point.get(value_key)}",
            ).add_to(validation_map)

    folium.LayerControl().add_to(validation_map)
    return st_folium(validation_map, height=height, use_container_width=True)
