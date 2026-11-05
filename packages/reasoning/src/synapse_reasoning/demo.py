"""End-to-end hybrid reasoning demonstration on synthetic lab envelopes.

Live /proc collector output is a separate dataset and must not be mixed with
these constructed event ids.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from synapse_correlation.demo import (
    ROOT,
    _admin_token,
    _ensure_api_environment,
    _http_json,
    _ingest,
    _load_env,
    _stamp,
)
from synapse_telemetry.signatures import generate_signing_key


def main() -> int:
    from synapse_agent.log import configure_logging, log_event

    configure_logging()
    _load_env()
    _ensure_api_environment()
    from alembic import command
    from alembic.config import Config

    if __import__("os").environ.get("MIGRATION_DATABASE_URL"):
        command.upgrade(Config(str(ROOT / "apps" / "api" / "alembic.ini")), "head")
    migration = __import__("os").environ.pop("MIGRATION_DATABASE_URL", None)
    from synapse_api.config import get_settings
    from synapse_api.db import reset_engine
    from synapse_api.main import create_app

    get_settings.cache_clear()
    reset_engine()
    import threading

    import uvicorn

    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18082, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not server.started:
        time.sleep(0.05)
    if not server.started:
        return 1
    base = "http://127.0.0.1:18082"
    os = __import__("os")
    try:
        token = _admin_token()
        expiry = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        status, created = _http_json(
            f"{base}/api/v1/targets",
            {
                "name": "reasoning-lab",
                "owner": "research-team",
                "scope": {
                    "environment": "lab",
                    "assets": ["reasoning-lab.internal"],
                    "description": "Synthetic hybrid reasoning demonstration.",
                },
                "authorization_expiry": expiry,
                "allowed_capabilities": ["telemetry.ingest"],
            },
            token=token,
        )
        if status != 201:
            return 1
        target_id = created["id"]
        key = generate_signing_key()
        agent_id = str(uuid4())
        boot_id = str(uuid4())
        enrolled, _body = _http_json(
            f"{base}/api/v1/targets/{target_id}/agents",
            {"public_key_hex": key.public_key().raw_bytes().hex(), "agent_id": agent_id},
            token=token,
        )
        if enrolled != 201:
            return 1
        common = {"target_id": target_id, "agent_id": agent_id, "boot_id": boot_id}
        _ingest(
            base,
            key,
            {
                **common,
                "event_type": "process_started",
                "sequence": 1,
                "observed_at": _stamp(0),
                "pid": 100,
                "ppid": 1,
                "uid": 1000,
                "start_ticks": 1,
                "comm": "python3",
            },
        )
        _ingest(
            base,
            key,
            {
                **common,
                "event_type": "network_connection_observed",
                "sequence": 2,
                "observed_at": _stamp(1),
                "protocol": "tcp",
                "local_port": 40000,
                "remote_port": 443,
                "remote_address": "[ip]",
                "uid": 1000,
                "pid": 100,
            },
        )
        _ingest(
            base,
            key,
            {
                **common,
                "event_type": "process_exited",
                "sequence": 3,
                "observed_at": _stamp(2),
                "pid": 100,
                "start_ticks": 1,
            },
        )
        _ingest(
            base,
            key,
            {
                **common,
                "event_type": "process_started",
                "sequence": 4,
                "observed_at": _stamp(3),
                "pid": 200,
                "ppid": 1,
                "uid": 1000,
                "start_ticks": 9,
                "comm": "python3",
            },
        )
        sequence = 5
        for index in range(6):
            _ingest(
                base,
                key,
                {
                    **common,
                    "event_type": "network_connection_observed",
                    "sequence": sequence,
                    "observed_at": _stamp(3 + index),
                    "protocol": "tcp",
                    "local_port": 41000 + index,
                    "remote_port": 80 + index,
                    "remote_address": "[ip]",
                    "uid": 1000,
                    "pid": 200,
                },
            )
            sequence += 1
        corr, _cbody = _http_json(
            f"{base}/api/v1/targets/{target_id}/correlation/runs",
            {"window_seconds": 300},
            token=token,
        )
        if corr != 201:
            return 1
        status, assessment = _http_json(
            f"{base}/api/v1/targets/{target_id}/reasoning/assessments",
            {"window_seconds": 300, "dataset_label": "synthetic_lab"},
            token=token,
        )
        if status != 201:
            log_event("demo_assessment_failed", status=status)
            return 1
        unsafe_status, unsafe = _http_json(
            f"{base}/api/v1/reasoning/assessments/{assessment['id']}/decision-proposals/verify",
            {
                "kind": "execute_host_mitigation",
                "authorized": True,
                "in_scope": True,
                "human_approved": True,
            },
            token=token,
        )
        log_event(
            "demo_complete",
            dataset="synthetic_lab",
            note="constructed envelopes, not procfs samples",
            hypothesis=assessment.get("selected_hypothesis"),
            neural_unusual=assessment.get("neural", {}).get("unusual"),
            completeness=assessment.get("quality", {}).get("reconstruction_completeness"),
            counterfactual=assessment.get("counterfactual", {}).get("difference"),
            verification=assessment.get("verification", {}).get("status"),
            unsafe_solver=unsafe.get("solver_result"),
            unsafe_status=unsafe_status,
        )
        if unsafe.get("solver_result") != "unsat":
            return 1
        if not assessment.get("selected_hypothesis"):
            return 1
        return 0
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        if migration is not None:
            os.environ["MIGRATION_DATABASE_URL"] = migration
        get_settings.cache_clear()
        reset_engine()


if __name__ == "__main__":
    raise SystemExit(main())
