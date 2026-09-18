# SIH26161 Mock / Dummy Contract Data

All files in this package are **synthetic demo fixtures** intended for frontend/backend integration testing. They are not real hydraulic or historical measurements.

Contract version: **1.0.0**

## How to use

Serve `artifacts/` at the URL prefix `/mock-api/artifacts/` and use the JSON files under `json/` as mocked request/response payloads.

The frontend can start with the following mocked responses:

- `16_flood_query_response_both.json` → normal results page
- `17_flood_query_response_partial.json` → one model fails
- `18_impact_result.json` → impact panel
- `19_satellite_overlay_live.json` → live satellite overlay
- `20_satellite_overlay_fallback.json` → GEE fallback state
- `23_historical_validation_response.json` → historical comparison page
- `14_job_status_running.json` / `15_job_status_succeeded.json` → Add-a-Dam onboarding UI

## Main request fixtures

- `10_scenario_resolve_request_slider.json`
- `11_scenario_resolve_request_exact.json`
- `13_scenario_onboarding_request.json`

## Module-to-module fixtures

- `01_terrain_manifest.json`
- `02_physical_scenario_s60.json`
- `03_hydrograph_s60.json`
- `04_scenario_bundle_s60.json`
- `05_flood_simulation_result_delft3d.json`
- `06_flood_simulation_result_sph.json`
- `07_validation_result_delft3d.json`
- `08_validation_result_sph.json`
- `09_confidence_result.json`
- `21_historical_observation_bundle.json`
- `22_historical_validation_result.json`

## Artifact policy

JSON payloads use `/mock-api/artifacts/...` URLs exactly as a browser-facing API would. The actual mock files exist under `artifacts/`.

## Important

The values are intentionally synthetic. They exist to exercise UI states, schema validation, success/partial/fallback/error handling, maps, charts, timelines, comparison panels, and downloads.

## Frontend integration note

The JSON files intentionally use `/mock-api/artifacts/...` URLs. In a local mock server, mount the package `artifacts/` directory at that prefix. No frontend should depend on the package filesystem paths.
