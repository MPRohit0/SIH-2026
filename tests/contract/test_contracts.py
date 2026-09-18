"""Contract Schema and Fixture Validation Test for CI."""

from scripts.validate_contracts import main


def test_contracts_and_fixtures():
    """Verify that all schemas are valid Draft 2020-12 and golden fixtures conform."""
    main()
