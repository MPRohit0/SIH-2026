"""Contract Validation Script for SIH26161.

Validates that JSON schemas under contracts/schemas/ are valid JSON Schema Draft-07/2020-12
and validates corresponding sample fixtures under contracts/fixtures/.
"""

from __future__ import annotations

import json
from pathlib import Path
import jsonschema


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    schemas_dir = repo_root / "contracts" / "schemas"
    fixtures_dir = repo_root / "contracts" / "fixtures"

    print("==================================================")
    print("SIH26161 Contract Schema & Fixture Validation")
    print("==================================================")

    schema_files = list(schemas_dir.glob("*.schema.json"))
    print(f"Found {len(schema_files)} schemas under {schemas_dir.relative_to(repo_root)}:")

    schemas = {}
    for schema_file in sorted(schema_files):
        with open(schema_file, "r", encoding="utf-8") as f:
            try:
                schema_json = json.load(f)
                jsonschema.Draft202012Validator.check_schema(schema_json)
                schemas[schema_file.stem.replace(".schema", "")] = schema_json
                print(f"  [VALID] {schema_file.name}")
            except Exception as e:
                print(f"  [ERROR] {schema_file.name}: {e}")
                raise

    print("\nValidating sample fixtures against schemas:")
    mapping = {
        "failure_source": fixtures_dir / "failure_sources",
        "confidence_result": fixtures_dir / "confidence",
        "hydrograph": fixtures_dir / "hydrographs",
        "terrain_manifest": fixtures_dir / "terrain",
        "job_status": fixtures_dir / "jobs",
    }

    validated_count = 0
    for schema_name, target_dir in mapping.items():
        if target_dir.exists() and schema_name in schemas:
            schema = schemas[schema_name]
            for fix_file in target_dir.glob("*.json"):
                with open(fix_file, "r", encoding="utf-8") as f:
                    fix_data = json.load(f)
                try:
                    jsonschema.validate(instance=fix_data, schema=schema)
                    print(f"  [PASS] {fix_file.relative_to(fixtures_dir)} matches {schema_name}")
                    validated_count += 1
                except jsonschema.ValidationError as ve:
                    print(f"  [FAIL] {fix_file.name}: {ve.message}")
                    raise

    print(f"\nAll {len(schema_files)} schemas and {validated_count} golden fixtures successfully validated!")
    print("==================================================")


if __name__ == "__main__":
    main()
