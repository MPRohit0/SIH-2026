# M2 Scientific Specification

## Status

**LOCKED SCIENTIFIC SPECIFICATION - VERSION 1.0**

This document is the complete scientific authority for Module 2 (Breach
Parameter Engine). M2 may implement only relationships explicitly stated
here and in the canonical handoff contract:

- [DATA_HANDOFF_CONTRACT.md](../contracts/DATA_HANDOFF_CONTRACT.md)

Developers MUST NOT:

- substitute an equation from another paper or version;
- infer or fill in coefficients, exponents, correction factors, or variables;
- combine equations from different methods without explicit approval;
- invent a severity-to-physics mapping;
- invent a hydrograph shape;
- label a hydraulic-solver output as an empirical estimate;
- treat an unavailable value as zero.

If a required equation, variable definition, applicability condition, unit, or
mapping is absent or ambiguous, implementation MUST STOP and report the
unresolved item. This document does not authorize a guessed implementation.

---

## 1. Scope and responsibility

M2 is responsible for:

- validating `FailureSource` and scenario inputs;
- resolving a scenario from an approved scenario catalog or exact physical
  inputs;
- estimating breach parameters using an explicitly selected empirical method;
- preserving method and value provenance;
- producing a contract-compatible `PhysicalScenario`.

M2 is not responsible for:

- processing DEM, land-cover, or terrain data;
- running Delft3D or DualSPHysics;
- generating an arbitrary hydrograph;
- calculating flood extent, depth, velocity, or arrival-time products;
- interpolation or scenario-cache lookup algorithms owned by M5;
- impact or loss analysis;
- satellite processing;
- map rendering;
- Streamlit or FastAPI integration.

M2 does not generate a `DischargeSeries` unless a separate authoritative
project specification explicitly supplies and approves a hydrograph-generation
method. Under this specification, empirical breach methods alone do not
authorize M2 to generate one.

---

## 2. Contract semantics used by this specification

### 2.1 Breach parameter ownership

`BreachParameters` describes one empirical breach-method estimate:

```text
BreachParameters {
  breach_width_m: float
  breach_depth_m: float
  formation_time_hr: float
  peak_discharge_m3s: float | null
  method: "froehlich" | "macdonald_langridge_monopolis"
  peak_discharge_provenance: object | null
}
```

`peak_discharge_m3s` is nullable:

- `null` means that the selected method, as approved here, does not provide a
  scientifically supported peak-discharge estimate for this result;
- a numeric value means that the selected method provides the estimate and the
  provenance object identifies its source;
- zero is a computed value and MUST NOT represent unavailable data.

The current repository schemas are placeholders. The detailed field
semantics are governed by the canonical handoff contract until those schemas
are revised.

### 2.2 Peak-discharge provenance

When a peak estimate is present, M2 MUST preserve its provenance:

```text
peak_discharge_provenance {
  source:
    "froehlich_2008"
    | "macdonald_langridge_monopolis"
    | "user_supplied"
    | "hydraulic_solver"
    | "unavailable"
  method_version: string | null
  input_basis: string | null
}
```

Rules:

- Froehlich (2008) results in this specification MUST use
  `peak_discharge_m3s = null` and `source = "unavailable"`.
- A MacDonald best-fit or envelope estimate MUST identify the selected
  MacDonald relationship.
- A hydraulic-solver peak belongs to `FloodSimulationResult`; it MUST NOT be
  copied into an empirical M2 `BreachParameters` record.
- `source = "hydraulic_solver"` is reserved for a contract context that
  explicitly permits solver provenance. It does not make the value an M2
  empirical estimate.

### 2.3 Scenario and hydrograph handoff

The canonical M2 handoff is:

```text
ScenarioBundle {
  schema_version: string
  scenario: PhysicalScenario
  discharge_series: DischargeSeries | null
}
```

When `discharge_series` is non-null:

```text
scenario.discharge_series_id == discharge_series.series_id
```

When M2 has no approved hydrograph:

```text
discharge_series = null
scenario.discharge_series_id = null
```

Downstream solver forcing in that case requires a separately specified M3/M4
contract. No consumer may fabricate a series from breach parameters.

The canonical identifier is `series_id`. Existing `hydrograph_id` fixture
fields are legacy compatibility fields and are not a new M2 output name.

### 2.4 Severity and exact scenarios

The only approved severity relationship is:

```text
severity_index = severity_level_0_10 * 10
```

This is a normalized scenario/catalog axis. It is not a physical statement
about breach height, width, volume, or discharge.

No equation is approved for deriving the following from severity:

- breach width;
- breach depth;
- formation time;
- peak discharge;
- initial water level;
- downstream discharge.

Severity therefore resolves through a site-specific scenario catalog/cache or
through explicitly approved engineering assumptions. M2 MUST NOT invent
arbitrary interpolation, multipliers, or ratios.

Exact physical mode may specify the contract fields:

```text
initial_water_level_m
breach_width_m
breach_depth_m
formation_time_hr
downstream_discharge_m3s
```

These are user-specified values. M2 MUST preserve them and MUST NOT silently
overwrite them with an empirical estimate.

For exact scenarios, `severity_index` is nullable unless the scenario matches
an approved catalog entry. A deterministic identifier or hash is not a
scientific severity mapping.

---

## 3. Froehlich (2008)

### 3.1 Applicability recorded by the project

The project specification permits this relationship set for:

- earthen dams;
- zoned earthen dams;
- earthfill dams with a core wall;
- rockfill dams.

The repository does not provide a more detailed classification procedure.
Classification rules beyond these categories remain unresolved.

### 3.2 Average breach width

The approved relationship is:

```text
B_avg = 0.27 * K0 * Vw^0.32 * hb^0.04
```

Variables and units:

```text
B_avg = average breach width, m
K0    = overtopping coefficient or piping/seepage coefficient
Vw    = reservoir volume at the time of failure, m^3
hb    = height of the final breach, m
```

Coefficient:

```text
K0 = 1.3  for overtopping
K0 = 1.0  for piping/seepage
```

The repository does not define a permitted `K0` value for other trigger
types. Such a request is unresolved and MUST NOT silently use either value.

### 3.3 Breach formation time

The approved relationship is:

```text
tf = 63.2 * sqrt(Vw / (g * hb^2))
```

Variables and units:

```text
tf = formation time produced by the equation, seconds
Vw = reservoir volume at the time of failure, m^3
hb = height of the final breach, m
g  = 9.80665 m/s^2
```

The coefficient and equation produce seconds. The contract represents
formation time in hours, so M2 MUST convert explicitly:

```text
formation_time_hr = tf_seconds / 3600
```

No other time conversion is authorized.

### 3.4 Side slopes

The approved side-slope relationships are:

```text
overtopping:   1.0H:1V
piping/seepage: 0.7H:1V
```

The current `BreachParameters` contract does not include side-slope fields.
If M3/M4 require these values, the contract must be extended explicitly.
M2 MUST NOT hide them in an undocumented field.

### 3.5 Peak discharge limitation

Froehlich (2008), as used by this project, does **not** provide the
peak-discharge equation used by the project.

Therefore:

- M2 MUST NOT calculate `peak_discharge_m3s` from Froehlich (2008);
- M2 MUST set it to `null` for a Froehlich-only estimate;
- M2 MUST NOT use a Froehlich (1995) peak-flow equation as a substitute;
- M2 MUST NOT copy a hydraulic-solver peak into the Froehlich estimate;
- M2 MUST NOT generate a hydrograph and label it Froehlich (2008).

---

## 4. MacDonald-Langridge-Monopolis (1984)

Only the relationships in this section are approved.

### 4.1 Earthfill eroded volume

For earthfill:

```text
V_eroded = 0.0261 * (V_out * h_w)^0.769
```

### 4.2 Earthfill with clay core or rockfill

For earthfill with clay core or rockfill:

```text
V_eroded = 0.00348 * (V_out * h_w)^0.852
```

Variables and units:

```text
V_eroded = eroded embankment volume, m^3
V_out    = volume of water passing through the breach, m^3
h_w      = water depth above the breach bottom, m
```

The repository does not define how material classification is established for
every `FailureSource`. M2 MUST stop with a validation error when the selected
formulation cannot be selected from available, authoritative inputs.

### 4.3 Formation time

For the approved earthfill formulation:

```text
tf = 0.0179 * V_eroded^0.364
```

`tf` is in hours, and therefore already matches the contract unit
`formation_time_hr`.

The repository does not explicitly approve a separate formation-time
relationship for the clay-core/rockfill volume equation. M2 MUST NOT infer
one.

### 4.4 Breach geometry

Approved side slopes:

```text
0.5H:1V
```

Approved bottom-width relationship:

```text
Wb =
[
  V_eroded - hb^2 * (C * Zb + hb * Zb * Z3 / 3)
]
/
[
  hb * (C + hb * Z3 / 2)
]
```

Variables:

```text
Wb = breach bottom width, m
hb = final breach height, m
C  = dam crest width, m
Z1 = upstream dam slope
Z2 = downstream dam slope
Z3 = Z1 + Z2
Zb = 0.5
```

The repository does not currently define authoritative values or ownership
for `C`, `Z1`, `Z2`, or all method-specific material classifications. M2
MUST NOT invent defaults for them.

### 4.5 Peak discharge

The project-approved MacDonald best-fit relationship is:

```text
Qp = 1.154 * (Vw * hw)^0.412
```

The project-approved alternative envelope relationship is:

```text
Qp_envelope = 3.85 * (Vw * hw)^0.411
```

Variables and units:

```text
Qp          = peak discharge, m^3/s
Qp_envelope = envelope peak discharge, m^3/s
Vw          = reservoir volume at failure, m^3
hw          = water depth used by the relationship, m
```

The best-fit and envelope equations are distinct:

- best-fit is the project default;
- envelope is an explicitly selected alternative;
- the envelope MUST NOT silently replace the best-fit equation;
- the selected relationship MUST be recorded in
  `peak_discharge_provenance.method_version` or an equivalent approved
  contract field.

These are empirical breach estimates. They are not hydraulic-solver outputs.

### 4.6 Iterative limitation

`V_out` is not known exactly before hydraulic simulation. A first estimate may
use the reservoir water volume at breach initiation only if that assumption is
explicitly recorded and approved for the run.

After hydraulic simulation, the actual breach outflow volume may require
re-estimation of MacDonald parameters. This iterative workflow is a system
behavior, not permission to invent a pre-simulation value or hydrograph.

---

## 5. Hydrographs and discharge series

M2 MUST NOT generate a triangular, trapezoidal, parabolic, linear, or other
arbitrary hydrograph under this specification.

Neither the approved Froehlich (2008) relationships nor the approved
MacDonald-Langridge-Monopolis (1984) relationships provide sufficient
information to define an arbitrary time-series shape for this project.

The hydraulic solver or a separately approved forcing component is
responsible for producing solver discharge series. Its output is distinct
from M2 empirical breach estimates and belongs to the solver result contract.

The repository does not yet define the complete M3/M4 contract for producing
time-dependent forcing when `ScenarioBundle.discharge_series` is null. That
boundary is unresolved and MUST be specified before implementation requiring
such forcing.

---

## 6. Provenance and downstream distinction

Downstream modules MUST be able to distinguish:

1. empirical breach estimates;
2. user-specified exact physical inputs;
3. catalog-resolved scenario values;
4. hydraulic-solver outputs.

At minimum:

- M2 method provenance identifies Froehlich or MacDonald;
- MacDonald best-fit versus envelope is identified;
- unavailable empirical peaks are represented by `null`, not zero;
- solver peak discharge is stored in `FloodSimulationResult`;
- solver output is never relabeled as Froehlich or MacDonald output.

The exact final provenance field shape is a contract revision item. Until that
shape is approved, M2 MUST NOT invent a new undocumented payload field.

---

## 7. Unresolved scientific and contract items

The following ownership rules are now resolved for the MacDonald contract
inputs:

- `PhysicalScenario.macdonald_inputs` is the explicit owner of MacDonald
  method-specific inputs.
- `V_out_m3` is the caller-supplied volume of water passing through the breach.
  M2 MUST NOT derive it from `FailureSource.storage_volume_m3`.
- `h_w_m` is the caller-supplied water depth above the breach bottom. M2 MUST
  NOT derive it from `initial_water_level_m` or `breach_depth_m`.
- `Vw_m3` is the caller-supplied reservoir volume at failure. It is distinct
  from `FailureSource.storage_volume_m3`.
- `hw_m` is the caller-supplied water depth used by the peak-discharge
  relationship. It is distinct from `h_w_m`.
- `crest_width_C_m`, `upstream_slope_Z1`, and `downstream_slope_Z2` are
  caller-supplied dam geometry inputs. Slope values are dimensionless ratios.
- `material_classification` explicitly selects `earthfill` or
  `earthfill_clay_core_rockfill`.
- `peak_discharge_relationship` explicitly selects `best_fit` or `envelope`;
  `best_fit` is the project default, while `envelope` must be explicitly
  selected.
- All MacDonald numeric inputs are mandatory and strictly positive when the
  MacDonald method is selected. Missing values produce a structured
  insufficient-input condition rather than defaults.
- These inputs remain separate from `BreachParameters`, which contains only
  empirical results.

The following remain unresolved:

- whether `eroded_volume_m3` must be exposed in the contract;
- the M3/M4 forcing contract when no M2 discharge series exists;
- trigger values other than overtopping and piping/seepage for Froehlich `K0`;
- how exact scenarios participate in M5 interpolation when no approved severity
  catalog mapping exists.

The approved MacDonald formation-time relationship applies only to the
`earthfill` formulation. No formation-time equation is defined for
`earthfill_clay_core_rockfill`; M2 MUST NOT infer one or make
`formation_time_hr` nullable.

No implementation may resolve these items by assumption.

---

## 8. Scientific Sources

The project-approved references are:

1. Froehlich, D. C. (2008), *Embankment Dam Breach Parameters and Their
   Uncertainties*.
2. MacDonald, T. C., and Langridge-Monopolis, J. (1984), *Breaching
   Characteristics of Dam Failures*.
3. HEC-RAS Hydraulic Reference Manual / Technical Reference, as identified by
   the project scientific specification.
4. USBR technical material documenting the approved empirical equations, as
   identified by the project scientific specification.

The repository does not currently include full bibliographic editions,
publication identifiers, page numbers, or embedded source copies for these
references. Those citation details remain unresolved; no additional equation
may be imported from them unless the exact project-approved formulation is
provided.
