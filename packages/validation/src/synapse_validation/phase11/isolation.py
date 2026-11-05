"""Keep flow benchmarks off the enrolled telemetry trust boundary."""


def assert_no_trust_boundary_crossing(source: str) -> None:
    if "from synapse_api" in source or "import synapse_api" in source:
        raise AssertionError("flow benchmarks must not import the API process")
    if "import sqlalchemy" in source or "from sqlalchemy" in source:
        raise AssertionError("flow benchmarks must not open the evidence database")
