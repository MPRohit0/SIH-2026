This document is the canonical interface contract for the SIH26161 system. It is designed so every module can be implemented independently against mocks and later integrated without changing field names, meanings, or failure semantics.

---

# 1. Global Conventions

## 1.1 Schema version

Every JSON request and response contains:

```
"schema_version": "1.0.0"
```

Semantic versioning:

- Major: breaking schema/semantic change.
    
- Minor: backward-compatible field/enum addition.
    
- Patch: clarification/implementation correction with no contract change.
    

A receiver must reject a major-version mismatch with `schema_version_mismatch`; it must never guess a schema.

## 1.2 API response status

Every **response** uses exactly:

```
status = "ok" | "partial" | "error"
```

- `ok`: the requested operation succeeded and all requested sub-results are available.
    
- `partial`: usable data exists, but one or more requested sub-results are unavailable/failed. `warnings` explains them.
    
- `error`: the requested operation itself failed and no usable result is returned.
    

Requests do not contain `status`.

## 1.3 Universal warnings/error envelope

Every response contains:

```
"warnings": []
```

For `status="partial"`, `warnings` must contain at least one item.

For `status="ok"` and `status="error"`, `warnings` is normally an empty array.

Each warning/error uses:

```
{
  "error_code": "snake_case_stable_code",
  "message": "Human readable message",
  "retryable": false,
  "details": null
}
```

`details` is a JSON object when structured context exists, otherwise `null`.

A top-level failed response is:

```
{
  "schema_version": "1.0.0",
  "status": "error",
  "warnings": [],
  "error": {
    "error_code": "...",
    "message": "...",
    "retryable": false,
    "details": null
  }
}
```

## 1.4 Null vs omitted vs zero

- Required fields are always present.
    
- `null` means the concept applies to the payload but no meaningful value was computed/available.
    
- `0`, `0.0`, `[]`, and `{}` mean the value was computed and is genuinely zero/empty.
    
- Optional fields may be omitted only when the entire concept does not apply to that payload.
    
- A missing required field is a contract violation, not an implicit `null`.
    

Examples:

```
population = 0        → computed, nobody exposed
population = null     → population result unavailable
population omitted    → invalid payload unless the field is explicitly optional
```

## 1.5 Confidence semantics

Confidence values are:

```
"HIGH" | "MODERATE" | "LOW" | null
```

- `null`: there is no prediction/result to assess.
    
- `LOW`: a prediction exists, but validation indicates it is unreliable.
    
- `MODERATE`: prediction exists with intermediate validation support.
    
- `HIGH`: prediction exists with strong validation support.
    

## 1.6 Coordinates and CRS

- API-facing coordinate arrays are always `[lon, lat]` in WGS84 / EPSG:4326.
    
- API-facing GeoJSON is always EPSG:4326.
    
- Stored rasters may use a projected CRS.
    
- Every geospatial `Artifact` carries its actual storage CRS.
    
- Every raster artifact has a WGS84 `bbox` even when stored in a projected CRS.
    
- No consumer may assume raster CRS from the global API CRS.
    

## 1.7 Time

- Timestamps are ISO 8601 UTC, e.g. `2026-09-18T10:15:00Z`.
    
- Simulation-relative times use `t_min` in minutes from simulation start.
    
- Dates without times use ISO `YYYY-MM-DD`.
    

## 1.8 Units

|Quantity|Unit|
|---|---|
|Coordinates|degrees|
|DEM / water level / depth|m|
|breach width/depth|m|
|formation time|hr|
|discharge|m³/s|
|velocity|m/s|
|area|km²|
|arrival time|min|
|road length|km|
|agriculture area|km²|
|rainfall|mm|

## 1.9 Artifact policy

Dashboard-facing interfaces never return raw filesystem paths. They return an `Artifact`.

Internal offline module handoffs may use the same `Artifact` abstraction even though modules share a filesystem.

```
Artifact.url is nullable only when available=false.
available=true  → url must be non-null
available=false → url must be null
```

## 1.10 Raster standard

Every raster artifact has:

```
"raster_meta": {
  "dtype": "float32" | "float64" | "int16" | "int32" | "uint8",
  "bands": [
    { "name": "depth", "unit": "m" }
  ],
  "nodata_value": -9999.0,
  "pixel_size_m": 30.0
}
```

`Artifact.crs` is the only CRS field; it is not duplicated inside `raster_meta`.

## 1.11 GeoJSON standard

Every GeoJSON artifact is a `FeatureCollection`, never a bare `Polygon`, `MultiPolygon`, or `Geometry`.

Each feature must contain at least:

```
"properties": {
  "source": "delft3d"
}
```

A valid zero-flood extent is:

```
{
  "type": "FeatureCollection",
  "features": []
}
```

## 1.12 Flood extent definition

A cell is considered flooded when:

```
depth >= flood_extent_threshold_m
```

The default system threshold is `0.30 m` and the value actually used is recorded in every `FloodSimulationResult`.

This threshold applies consistently to timestep extents, maximum extent, and arrival-time calculation.

---

# 2. Canonical Shared Types

## 2.1 SiteContext

```
SiteContext {
  site_id: string
  name: string
  bbox_wgs84: [min_lon, min_lat, max_lon, max_lat]
  failure_source_id: string
}
```

Validation:

- `min_lon < max_lon`
    
- `min_lat < max_lat`
    
- longitude within `[-180, 180]`
    
- latitude within `[-90, 90]`
    

## 2.2 FailureSource

Replaces dam-only assumptions and supports engineered dams, GLOFs, and landslide-dammed lakes.

```
FailureSource {
  failure_source_id: string
  type: "engineered_dam" | "natural_lake_glof" | "landslide_dam"
  name: string
  location: { lon: float, lat: float }
  height_m: float | null
  storage_volume_m3: float | null
  catchment_area_km2: float | null
  data_source: string | null
}
```

`height_m` may be null for a source where barrier height is unknown/not applicable.

## 2.3 Artifact

```
Artifact {
  artifact_id: string
  kind: "raster" | "vector" | "file"
  media_type: string
  url: string | null
  crs: string | null
  raster_meta: RasterMeta | null
  bbox_wgs84: [float,float,float,float] | null
  checksum: string | null
  available: boolean
}
```

Rules:

- `kind="raster"` → `raster_meta` required and `crs` required.
    
- `kind="vector"` → `crs` required.
    
- `kind="file"` → `crs` may be null for non-geospatial files.
    
- `available=false` → `url=null`.
    

## 2.4 RasterMeta

```
RasterMeta {
  dtype: "float32" | "float64" | "int16" | "int32" | "uint8"
  bands: [{ name: string, unit: string }]
  nodata_value: number | null
  pixel_size_m: float
}
```

## 2.5 BreachParameters

Represents **one** breach-model estimate. `method` is singular.

```
BreachParameters {
  breach_width_m: float
  breach_depth_m: float
  formation_time_hr: float
  peak_discharge_m3s: float | null
  method: "froehlich" | "macdonald_langridge_monopolis"
  peak_discharge_provenance: {
    source: "froehlich_2008"
      | "macdonald_langridge_monopolis"
      | "user_supplied"
      | "hydraulic_solver"
      | "unavailable"
    method_version: string | null
    input_basis: string | null
  } | null
}
```

Validation:

- `breach_width_m > 0 && <= 500`
    
- `breach_depth_m > 0`
    
- if `FailureSource.height_m != null`, `breach_depth_m <= height_m`
    
- if `FailureSource.height_m == null`, only the positive lower bound is enforced
    
- `0.05 <= formation_time_hr <= 48`
    
- if `peak_discharge_m3s != null`, `0 < peak_discharge_m3s <= 100000`
    
- when a discharge series is present and the peak is a series summary,
  `peak_discharge_m3s == max(discharge_series.points[].discharge_m3s)` within
  defined floating-point tolerance
- `null` means no scientifically supported peak estimate is available from
  the selected M2 method; it does not mean zero
- peak-discharge provenance must distinguish empirical estimates,
  user-supplied values, hydraulic-solver outputs, and unavailable values
    

If both breach formulas are run, Module 2 creates **separate PhysicalScenario objects**, one per selected method. They must have distinct `scenario_id`s.

## 2.6 DischargeSeries

Used for approved model forcing hydrographs and observed historical discharge
series. M2 does not generate one unless an independently approved hydrograph
method exists.

```
DischargeSeries {
  series_id: string
  points: [
    {
      t_min: float
      discharge_m3s: float
    }
  ]
}
```

Rules:

- at least 2 points
    
- `points[0].t_min == 0` for model-generated hydrographs
    
- strictly increasing `t_min`
    
- no duplicate timestamps
    
- `t_min >= 0`
    
- `discharge_m3s >= 0`
    

Observed historical series may use an absolute observation time mapped into `t_min` relative to the event start.

## 2.7 PhysicalScenario

This is the canonical scenario passed to the hydraulic models.

```
PhysicalScenario {
  scenario_id: string
  site_id: string
  failure_source_id: string

  severity_index: int | null          // 0..100 when catalog-resolved
  severity_level_0_10: int | null     // original UI slider level, if slider mode was used

  initial_conditions: {
    initial_water_level_m: float | null
    downstream_discharge_m3s: float | null
  }

  breach: BreachParameters
  macdonald_inputs: MacDonaldInputs | null
  discharge_series_id: string | null

  breach_engine_version: string
  generated_at: string
}

MacDonaldInputs {
  material_classification:
    "earthfill" | "earthfill_clay_core_rockfill"
  V_out_m3: float
  h_w_m: float
  Vw_m3: float
  hw_m: float
  crest_width_C_m: float
  upstream_slope_Z1: float
  downstream_slope_Z2: float
  peak_discharge_relationship: "best_fit" | "envelope"
}
```

`macdonald_inputs` is a method-specific input namespace and is not part of
`BreachParameters`, which remains the empirical result object.

When `breach.method == "macdonald_langridge_monopolis"`, `macdonald_inputs`
is required and every field in it is required:

- `material_classification` selects the approved eroded-volume relationship:
  `earthfill` or `earthfill_clay_core_rockfill`.
- `V_out_m3` is `V_out`, the volume of water passing through the breach, in m³.
- `h_w_m` is `h_w`, the water depth above the breach bottom, in m.
- `Vw_m3` is `Vw`, the reservoir volume at failure, in m³.
- `hw_m` is `hw`, the water depth used by the peak-discharge relationship, in m.
- `crest_width_C_m` is `C`, the dam crest width, in m.
- `upstream_slope_Z1` is `Z1`, the upstream dam slope ratio, dimensionless.
- `downstream_slope_Z2` is `Z2`, the downstream dam slope ratio, dimensionless.
- `peak_discharge_relationship` selects the MacDonald peak relationship.
  `best_fit` is the project default; `envelope` is an explicit alternative.

All numeric MacDonald inputs are strictly positive. No field is inferred from
`FailureSource.storage_volume_m3`, `initial_water_level_m`, or
`breach_depth_m`. `FailureSource.storage_volume_m3` remains a general source
storage value and is not redefined as `Vw` or `V_out`.

When `breach.method != "macdonald_langridge_monopolis"`, `macdonald_inputs`
must be `null` or omitted only where the containing schema permits omission;
it must not affect Froehlich calculations.

The approved MacDonald formation-time relationship applies only to the
earthfill formulation. No clay-core/rockfill formation-time relationship is
defined. Therefore, a clay-core/rockfill request must remain a structured
insufficient-input condition until an approved formation-time relationship or
user-supplied contract result is available. `formation_time_hr` remains
mandatory in `BreachParameters`.

`severity_index` is an abstract normalized index. It is **not** a statement
that a percentage of dam height failed. For slider scenarios,
`severity_index = severity_level_0_10 * 10`. Exact scenarios may use `null`
unless they match an approved site-specific scenario catalog entry.

`scenario_id` is stable and content-addressed from the canonical scenario fields; `generated_at` is **not** part of the hash.

## 2.8 Domain

```
Domain {
  domain_type: "full_reach" | "near_field"
  bbox_wgs84: [float,float,float,float]
  geometry: Artifact                       // vector FeatureCollection
  comparison_overlap: Artifact | null     // common comparison region, if applicable
}
```

If `comparison_overlap` is non-null, its geometry must be contained in both model domains and be used for cross-model comparison metrics.

## 2.9 FloodSimulationResult

The exact same shape is produced by Module 3 and Module 4.

```
FloodSimulationResult {
  schema_version: string
  status: "ok" | "partial" | "error"
  warnings: [Error]
  error: Error | null

  run_id: string
  scenario_id: string
  model: "sph" | "delft3d"
  model_version: string
  domain: Domain
  terrain_manifest_id: string

  timesteps: [
    {
      t_min: float
      depth: Artifact
      velocity: Artifact
      extent: Artifact
    }
  ]

  max_extent: Artifact
  arrival_time: Artifact
  flood_extent_threshold_m: float

  peak_discharge_m3s: float | null
  max_depth_m: float | null
  max_velocity_ms: float | null
  inundated_area_km2: float | null

  runtime_sec: float | null
  config_hash: string
  generated_at: string
}
```

Rules:

- `timesteps` must contain at least one entry for `status=ok` or `partial`.
    
- `timesteps[].t_min` strictly increasing; no duplicates.
    
- Any unavailable artifact is represented by `available=false`, not by a fabricated path.
    
- Scalar summaries are null when not computed.
    
- `inundated_area_km2`, when non-null, is the area of `max_extent`.
    
- `arrival_time` is minutes to the first timestep where depth meets/exceeds the threshold.
    
- If no usable output exists, `status=error` and `timesteps` may be omitted/empty.
    

## 2.10 ValidationResult — interpolation holdout

```
ValidationResult {
  schema_version: string
  validation_id: string
  validation_profile_id: string
  confidence_formula_version: string

  held_out_scenario_id: string
  model: "sph" | "delft3d"

  interpolation_method: string
  source_neighbors: [
    {
      scenario_id: string
      severity_index: int
      weight: float
    }
  ]

  metrics: {
    flood_extent_iou: float | null
    relative_area_error_pct: float | null
    flood_depth_mae_m: float | null
    arrival_time_mae_min: float | null
    velocity_mae_ms: float | null
  }

  metric_availability: {
    flood_extent_iou: "computed" | "unavailable_no_holdout" | "unavailable_no_overlap" | "unavailable_invalid_reference"
    relative_area_error_pct: same enum
    flood_depth_mae_m: same enum
    arrival_time_mae_min: same enum
    velocity_mae_ms: same enum
  }

  generated_at: string
}
```

`holdout_sample_count` is derived as `source_neighbors.length`; it does not need to be duplicated.

## 2.11 ConfidenceResult

```
ConfidenceResult {
  schema_version: string
  confidence_formula_version: string
  validation_profile_id: string | null

  overall: "HIGH" | "MODERATE" | "LOW" | null
  flood_extent: "HIGH" | "MODERATE" | "LOW" | null
  flood_depth: "HIGH" | "MODERATE" | "LOW" | null
  arrival_time: "HIGH" | "MODERATE" | "LOW" | null
  velocity: "HIGH" | "MODERATE" | "LOW" | null
}
```

The formula itself is versioned outside this payload. The response must not invent weights or thresholds independently per module.

## 2.12 PerModelFloodResult

```
PerModelFloodResult {
  scenario_id: string

  interpolation: {
    is_interpolated: boolean
    neighbors: [
      {
        severity_index: int
        scenario_id: string
        weight: float
      }
    ]
    interpolation_method: string | null
  }

  timesteps: [
    {
      t_min: float
      depth: Artifact
      velocity: Artifact
      extent: Artifact
    }
  ]

  max_extent: Artifact
  arrival_time: Artifact
  peak_discharge_m3s: float | null
  max_depth_m: float | null
  max_velocity_ms: float | null
  inundated_area_km2: float | null

  confidence: ConfidenceResult
}
```

If a model was requested but no result exists, its entry is `null` and the top-level response uses `status="partial"` or `status="error"` according to §3.6.

## 2.13 ImpactResult

```
ImpactResult {
  schema_version: string
  status: "ok" | "partial" | "error"
  warnings: [Error]
  error: Error | null

  scenario_id: string
  model: "sph" | "delft3d"

  affected_population: int | null
  population_data_availability: "computed" | "dataset_unavailable"

  affected_buildings: int | null
  buildings_data_availability: "computed" | "dataset_unavailable"

  affected_roads_km: float | null
  roads_data_availability: "computed" | "dataset_unavailable"

  affected_agriculture_km2: float | null
  agriculture_data_availability: "computed" | "dataset_unavailable"

  critical_infrastructure: [
    {
      type: "hospital" | "school" | "other"
      name: string
      location: { lon: float, lat: float }
    }
  ]
  critical_infrastructure_data_availability: "computed" | "dataset_unavailable"

  exports: {
    shp: Artifact | null
    kml: Artifact | null
    geojson: Artifact | null
  }

  generated_at: string
}
```

A valid zero result uses `0`/`0.0` and availability=`computed`.

An unavailable dataset uses `null` and availability=`dataset_unavailable`.

## 2.14 HistoricalObservationBundle

```
HistoricalObservationBundle {
  schema_version: string
  event_id: string
  failure_source_id: string
  historical_event_date: string

  extent: Artifact | null

  discharge_series: DischargeSeries | null

  arrival_time_points: [
    {
      location_id: string
      location: { lon: float, lat: float }
      arrival_time_min: float
    }
  ] | null

  depth_points: [
    {
      location_id: string
      location: { lon: float, lat: float }
      depth_m: float
    }
  ] | null

  velocity_points: [
    {
      location_id: string
      location: { lon: float, lat: float }
      velocity_ms: float
    }
  ] | null

  source_metadata: {
    source: string
    fetched_at: string
  }
}
```

`null` means the observation type is unavailable. `[]` means observations were available and there were zero records.

## 2.15 HistoricalValidationResult

```
HistoricalValidationResult {
  schema_version: string
  validation_id: string
  event_id: string
  failure_source_id: string
  historical_event_date: string
  model: "sph" | "delft3d"

  observations: HistoricalObservationAvailability

  metrics: {
    flood_extent_iou: float | null
    flood_extent_f1: float | null
    relative_area_error_pct: float | null
    arrival_time_mae_min: float | null
    peak_discharge_error_pct: float | null
    nse: float | null
    kge: float | null
  }

  metric_availability: {
    flood_extent_iou: string
    flood_extent_f1: string
    relative_area_error_pct: string
    arrival_time_mae_min: string
    peak_discharge_error_pct: string
    nse: string
    kge: string
  }

  generated_at: string
}
```

`nse` and `kge` are only computed when a sufficiently sampled observed discharge time series exists.

For a single arrival-time observation/location, the metric is reported as `arrival_time_error_min`; `arrival_time_mae_min` requires at least two comparable locations. The `metric_availability` field must state why a metric is null.

## 2.16 HistoricalObservationAvailability

```
HistoricalObservationAvailability {
  extent: Artifact | null
  discharge_series: DischargeSeries | null
  arrival_time_points: array | null
  depth_points: array | null
  velocity_points: array | null
}
```

---

# 3. Per-Interface Contracts

## 3.1 Module 1 → Module 3 / Module 4 — TerrainManifest

### Request/data object

```
TerrainManifest {
  schema_version
  terrain_manifest_id
  site_id
  failure_source_id
  status
  warnings
  error

  dem: Artifact
  landcover_classes: Artifact | null
  manning_n: Artifact | null
  river_centerline: Artifact
  cross_sections: Artifact | null
  sph_boundary_geometry: Artifact | null

  bbox_wgs84
  storage_crs
  api_crs: "EPSG:4326"
  dem_resolution_m
  generated_at
}
```

Rules:

- Delft3D requires `dem` and either `manning_n` or a documented model-default roughness configuration.
    
- SPH requires `dem` or `sph_boundary_geometry` according to the selected SPH workflow.
    
- `landcover_classes` is categorical LULC, not Manning's n.
    
- `manning_n` is already converted to roughness values.
    
- `cross_sections=null` is valid only when the model configuration does not require them.
    

Error example:

```
{
  "schema_version": "1.0.0",
  "status": "error",
  "warnings": [],
  "error": {
    "error_code": "dem_not_found",
    "message": "No DEM covers the requested bbox",
    "retryable": true,
    "details": {
      "site_id": "rishiganga_01",
      "bbox_wgs84": [79.72,30.50,79.90,30.65]
    }
  }
}
```

## 3.2 Module 2 → Module 3 / Module 4 — Scenario Bundle

### Request/data object

```
ScenarioBundle {
  schema_version
  scenario: PhysicalScenario
  discharge_series: DischargeSeries | null
}
```

Rules:

- when `discharge_series` is non-null,
  `scenario.discharge_series_id == discharge_series.series_id`
- when `discharge_series` is null, `scenario.discharge_series_id` must be null
- M2 must not invent a hydrograph shape; solver-side forcing requires an
  explicitly defined M3/M4 contract
- `series_id` is canonical; `hydrograph_id` is accepted only for legacy
  compatibility fixtures and is not a canonical M2 output field
    
- If Module 2 computes both breach formulas, it sends one `ScenarioBundle` per selected method/scenario.
    

Error:

```
missing_failure_source_specs
invalid_scenario_inputs
insufficient_exact_inputs
breach_formula_failed
```

A failure for one scenario does not invalidate other scenario levels in a batch; the orchestrator records that scenario as failed and continues where possible.

## 3.3 Module 3 / Module 4 → Module 5 — FloodSimulationResult

Both modules produce **exactly the same schema**.

No downstream module may special-case raw Delft3D or raw SPH output.

`model` and `model_version` are the only model identity fields; shared result fields are identical.

## 3.4 Dashboard → Orchestrator — Scenario Resolution

### POST `/scenarios/resolve`

Request:

```
ScenarioResolveRequest {
  schema_version
  site_id: string

  input_mode: "severity_slider" | "exact_values"

  severity_level_0_10: int | null

  exact_values: {
    initial_water_level_m: float | null
    breach_width_m: float | null
    breach_depth_m: float | null
    formation_time_hr: float | null
    downstream_discharge_m3s: float | null
  } | null
}
```

Rules:

- `severity_slider` → `severity_level_0_10` required and `exact_values=null`.
    
- `severity_level_0_10` maps to `severity_index = severity_level_0_10 * 10`.
    
- `exact_values` → `exact_values` object required; `severity_level_0_10=null`.
    
- Exact physical values do not receive a mathematical `severity_index`.
  A non-null value is allowed only when Module 2 resolves an approved
  site-specific scenario catalog entry.
    
- If insufficient values are provided for the selected failure-source type, return `insufficient_exact_inputs` with `details.required_fields`.
    

Response:

```
ScenarioResolutionResult {
  schema_version
  status
  warnings
  error
  scenario: PhysicalScenario
}
```

The returned `scenario.scenario_id` becomes the immutable reference used by `/flood` and `/impact`.

## 3.5 Dashboard → Orchestrator — Add-a-Dam

### POST `/sites/onboard`

Request:

```
SiteOnboardingRequest {
  schema_version

  site: {
    site_id: string
    name: string
    bbox_wgs84: [float,float,float,float]
  }

  failure_source: FailureSource

  severity_levels: [int]       // 0..100, unique, sorted ascending, min 2
  demo_mode: boolean
}
```

`site.bbox_wgs84` is now explicitly supplied; Module 1 no longer has to infer an AOI from a point.

Response:

```
{
  schema_version
  status: "ok" | "error"
  warnings
  error
  job_id: string
}
```

### GET `/jobs/{job_id}`

Returns `JobStatus`.

## 3.6 JobStatus — Orchestrator → Dashboard

```
JobStatus {
  schema_version

  // status describes whether the job-status request itself succeeded.
  status: "ok" | "error"
  warnings: [Error]
  error: Error | null

  job_id: string
  job_type:
    "onboard_site"
    | "recompute_scenario_grid"
    | "gee_refresh"
    | "validate_interpolation"
    | "validate_historical"

  state:
    "queued"
    | "running"
    | "succeeded"
    | "failed"
    | "partially_succeeded"

  progress_pct: float | null
  current_step: string | null

  steps: [
    {
      name: string
      state: "pending" | "running" | "done" | "failed"
      detail: string | null
    }
  ]

  estimated_completion: string | null
  result_ref: string | null
  errors: [Error]
  created_at: string
  updated_at: string
}
```

Job failure is represented by `state="failed"` or `state="partially_succeeded"`, not by changing the API response `status` to a separate enum.

## 3.7 Module 5 → Module 8 / Module 6 — `/flood`

### GET `/flood?scenario_id=...&models=sph,delft3d`

A flood query references `scenario_id`, never raw severity alone. This prevents two different exact physical scenarios from colliding on the same normalized severity index.

Response:

```
FloodQueryResponse {
  schema_version
  status: "ok" | "partial" | "error"
  warnings
  error

  scenario_id: string

  results: {
    sph: PerModelFloodResult | null
    delft3d: PerModelFloodResult | null
  }

  queried_at: string
}
```

Status rules:

- requested one model + it succeeds → `ok`
    
- requested two + one succeeds → `partial`
    
- requested two + both fail → `error`
    
- scenario not onboarded / job still running → `error` with `scenario_not_ready`, `retryable=true`
    

`PerModelFloodResult` contains all dashboard-required outputs: timestep animation data, max extent, arrival-time raster, velocity raster, peak discharge, depth, velocity, area, and confidence.

## 3.8 Module 5 → Module 6 — Impact input

Module 6 consumes the same `/flood` response as the Dashboard.

It must select a successful `PerModelFloodResult` by `scenario_id` + `model`.

If the selected model result is null/unavailable, `/impact` returns `upstream_flood_data_unavailable`.

## 3.9 Module 6 → Module 8 — `/impact`

### GET `/impact?scenario_id=...&model=sph|delft3d`

Returns `ImpactResult`.

Rules:

- population/buildings/roads/agriculture are independent datasets.
    
- One unavailable dataset makes the response `partial`, not `error`, if other outputs exist.
    
- `critical_infrastructure=[]` means computed zero matching affected assets.
    
- `critical_infrastructure=null` is not used; use the separate availability field.
    
- SHP export must be delivered as a downloadable package artifact (typically ZIP containing `.shp`, `.shx`, `.dbf`, `.prj`, etc.), not as a naked `.shp` file.
    

## 3.10 Scenario Cache Engine — internal subcontracts

### Cache lookup

```
lookup(scenario_id, model) → FloodSimulationResult | not_found
```

### Interpolation

```
interpolate(target_scenario, model, neighbors[]) → PerModelFloodResult
```

Rules:

- At least 2 neighboring scenarios required for the current linear/weighted severity-axis method.
    
- Every neighbor has a stable `scenario_id` and weight.
    
- Weights must be non-negative and sum to `1.0` within tolerance.
    
- If the target lies outside the validated scenario range, the engine must not silently extrapolate; return `interpolation_out_of_valid_range` and recommend a new physics run.
    

### Validation

```
validate(held_out_scenario, neighbor_scenarios) → ValidationResult
```

### Confidence

```
compute_confidence(validation_profile, model_agreement, input_distance, data_quality)
  → ConfidenceResult
```

## 3.11 Dashboard → Module 7 — `/satellite_overlay`

### GET `/satellite_overlay?failure_source_id=...&mode=latest|historical&date=...`

For `mode=latest`, `date=null`.

For `mode=historical`, `date` is required.

Response:

```
SatelliteOverlayResponse {
  schema_version
  status: "ok" | "partial" | "error"
  warnings
  error

  failure_source_id: string
  observation_date: string | null
  source: "sentinel1_sar" | "sentinel2" | "manual_screenshot" | null
  overlay: Artifact | null
  is_fallback: boolean
  fallback_reason: string | null
  fetched_at: string
}
```

Rules:

- `is_fallback=true` means the returned overlay is actually a fallback/cached artifact.
    
- `is_fallback=true` requires `overlay.available=true` and non-null `fallback_reason`.
    
- Live failure + fallback available → `status="partial"`.
    
- Live failure + no fallback → `status="error"`, `is_fallback=false`, `overlay=null`.
    

## 3.12 Module 7 → Module 5 — historical observation input

Module 7 provides a complete `HistoricalObservationBundle`.

Satellite data supplies the observed extent; other observational sources such as gauges/field reports may populate discharge, arrival-time, depth, and velocity observations.

Module 7 must never claim that an unobserved quantity came from Sentinel imagery.

If an observation type is unavailable, the corresponding field is `null`.

## 3.13 Module 5 → Module 8 — `/validation/historical`

### GET `/validation/historical?failure_source_id=...&event_id=...&model=...`

All query parameters except `failure_source_id` are optional filters.

Response:

```
HistoricalValidationResponse {
  schema_version
  status: "ok" | "partial" | "error"
  warnings
  error
  results: [HistoricalValidationResult]
}
```

If no validated historical event exists for the requested source/filter, return `ok` with `results=[]`.

---

# 4. Validation Rules and Domain Invariants

## 4.1 Scenario identity

`scenario_id` must identify the complete physical scenario, not merely severity.

A scenario changes if any of these change:

- failure source
    
- initial water level
    
- downstream discharge
    
- breach width
    
- breach depth
    
- formation time
    
- breach method
    
- other fields explicitly included in the scenario hash
    

`generated_at` and runtime information must not change `scenario_id`.

## 4.2 Interpolation validity

Interpolation is only permitted inside the validated scenario domain.

The engine must retain:

- source scenario IDs
    
- source severity indices
    
- weights
    
- interpolation method
    
- validation profile used for confidence
    

## 4.3 No silent extrapolation

A request outside the calibrated/validated scenario envelope returns:

```
interpolation_out_of_valid_range
```

rather than pretending that extrapolation is equivalent to interpolation.

## 4.4 Model symmetry

M3 and M4 must produce the same canonical `FloodSimulationResult` fields.

Raw solver formats never cross the M3/M4 → M5 boundary.

## 4.5 Historical metrics

`nse` and `kge` require an observed discharge time series.

`arrival_time_mae_min` requires multiple comparable observed locations. With exactly one location, report a single `arrival_time_error_min` in a separate extension field or mark MAE unavailable.

Depth/velocity MAE require multiple comparable observations or a spatial reference raster.

## 4.6 Partial failures

A partial result must never fabricate missing values as zero.

Example:

```
population = null
population_data_availability = dataset_unavailable
```

not:

```
population = 0
```

unless zero was actually computed.

---

# 5. Canonical Error Codes

## Terrain

```
dem_not_found
landcover_not_found
roughness_not_available
reprojection_failed
bbox_out_of_coverage
terrain_artifact_failed
```

## Scenario / Breach

```
failure_source_not_found
missing_failure_source_specs
invalid_scenario_inputs
insufficient_exact_inputs
severity_index_out_of_range
breach_formula_failed
hydrograph_invalid
```

## Simulation

```
simulation_did_not_converge
simulation_timeout
gpu_unavailable
input_hydrograph_missing
invalid_terrain_manifest
solver_configuration_invalid
```

## Cache / interpolation

```
scenario_not_found
scenario_not_ready
cache_read_failed
interpolation_out_of_valid_range
interpolation_insufficient_neighbors
interpolation_failed
validation_reference_missing
```

## Impact / export

```
upstream_flood_data_unavailable
dataset_unavailable
overlay_failed
export_write_failed
artifact_missing
```

## Satellite

```
gee_unreachable
gee_auth_failed
no_observation_available
no_fallback_available
satellite_processing_failed
```

## Contract

```
schema_version_mismatch
invalid_payload
missing_required_field
invalid_enum_value
invalid_units
invalid_geometry
```

---

# 6. Dependency / Interface Table

|From|To|Contract|Mode|
|---|---|---|---|
|M8 Dashboard|Orchestrator/M5|ScenarioResolveRequest|live sync|
|M8 Dashboard|Orchestrator|SiteOnboardingRequest|live async|
|Orchestrator|M1|Terrain/site job|async|
|M1 Terrain|M3 Delft3D|TerrainManifest|offline batch|
|M1 Terrain|M4 SPH|TerrainManifest|offline batch|
|M2 Breach|M3 Delft3D|ScenarioBundle|offline batch|
|M2 Breach|M4 SPH|ScenarioBundle|offline batch|
|M3 Delft3D|M5 Cache|FloodSimulationResult|offline batch|
|M4 SPH|M5 Cache|FloodSimulationResult|offline batch|
|M5 Cache|M8 Dashboard|`/flood`|live sync|
|M5 Cache|M6 Impact|`/flood`|live sync|
|M6 Impact|M8 Dashboard|`/impact`|live sync|
|M8 Dashboard|M7 GEE|`/satellite_overlay`|live sync/cached|
|M7 GEE|M5 Validation|HistoricalObservationBundle|offline/validation|
|M5 Validation|M8 Dashboard|`/validation/historical`|live sync|
|Orchestrator|Dashboard|`JobStatus`|live polling|

---

# 7. Canonical Development Rule

Every team member must be able to work using the contracts and mock artifacts without waiting for another module.

Recommended order:

```
Define canonical types
        ↓
Generate mock JSON + mock artifacts
        ↓
Build each module against mocks
        ↓
Implement real solver/data adapters
        ↓
Integration tests at contract boundaries
```

The contract is frozen only when:

1. Every interface has an owner.
    
2. Every request has exact fields and types.
    
3. Every response has exact fields and types.
    
4. Every nullable field has a defined meaning.
    
5. Every zero/empty state has a defined meaning.
    
6. Every partial/error state has a defined representation.
    
7. SPH and Delft3D emit the same `FloodSimulationResult`.
    
8. Scenario identity is reproducible.
    
9. Interpolation provenance and validation provenance are retained.
    
10. Dashboard-facing responses never expose raw filesystem paths.