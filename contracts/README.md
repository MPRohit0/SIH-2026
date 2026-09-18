# Contracts & Shared Schema Specifications

This directory contains the canonical specifications, JSON schemas, and golden fixtures governing data exchange across all SIH26161 modules.

## Hierarchy & Roles

1. **[DATA_HANDOFF_CONTRACT.md](DATA_HANDOFF_CONTRACT.md) — Human-Readable Source of Truth**
   - The authoritative interface contract across all sub-teams.
   - Defines field semantics, global coordinate systems (EPSG:4326), units, error codes, nullability rules, and failure modes.
   - All modules must adhere to these conventions to guarantee plug-and-play integration.

2. **[schemas/](schemas/) — Machine-Readable JSON Schemas**
   - Formal JSON Schema definitions (Draft 2020-12 / Draft 7) for every data structure.
   - Used for automated validation in CI, testing, and runtime boundaries.

3. **[fixtures/](fixtures/) — Canonical Contract Examples**
   - Golden-master valid examples of payloads directly conforming to `schemas/`.
   - Used in contract validation tests (`tests/contract/`) to verify schema integrity.

4. **[data/mock/](../data/mock/) — Synthetic Runtime & Demo Data (Separate from Contracts)**
   - Located under `data/mock/` (not within `contracts/`).
   - Contains end-to-end synthetic scenarios (`data/mock/json/`) and sample raster/vector artifacts (`data/mock/artifacts/`) used to run and test the UI and offline workflows without requiring live solvers or external data providers.

## Strict Rules
- Treat `contracts/` as read-only shared infrastructure.
- Never modify field names, units, or enums without updating `DATA_HANDOFF_CONTRACT.md` and bumping the semantic version in `contracts/VERSION`.
