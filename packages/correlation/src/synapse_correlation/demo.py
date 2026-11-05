"""Synthetic lab demonstration of evidence correlation.

Synthetic envelopes are constructed in this process and ingested through
the existing signed telemetry pipeline. They are not /proc samples. When
/proc is present, a second enrolled agent may also submit a live collector
poll; those event ids are printed separately.
"""

from __future__ import annotations

import json
import os
import secrets
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
from synapse_telemetry.normalization import normalize_observation
from synapse_telemetry.signatures import generate_signing_key, sign_event

ROOT = Path(__file__).resolve().parents[4]
LAB_TIME = datetime(2026, 9, 29, 17, 34, tzinfo=UTC)


def _load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for key, value in dotenv_values(env_file).items():
        if value is not None and key not in os.environ:
            os.environ[key] = value


def _ensure_api_environment() -> None:
    os.environ.setdefault("SYNAPSE_ENVIRONMENT", "local")
    os.environ.setdefault("SYNAPSE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    if not os.environ.get("SYNAPSE_AUTH_TOKENS", "").strip():
        admin = "demo-admin-" + secrets.token_hex(16)
        viewer = "demo-viewer-" + secrets.token_hex(16)
        os.environ["SYNAPSE_AUTH_TOKENS"] = json.dumps(
            {
                admin: {"actor": "demo-admin", "role": "admin"},
                viewer: {"actor": "demo-viewer", "role": "viewer"},
            }
        )
    if os.environ.get("DATABASE_URL", "").strip():
        return
    migration = os.environ.get("MIGRATION_DATABASE_URL", "").strip()
    password = os.environ.get("SYNAPSE_APP_PASSWORD", "").strip()
    if not migration or not password:
        raise RuntimeError("DATABASE_URL or migration settings are required")
    from sqlalchemy.engine import make_url

    os.environ["DATABASE_URL"] = (
        make_url(migration)
        .set(username="synapse_app", password=password)
        .render_as_string(hide_password=False)
    )


def _http_json(
    url: str,
    payload: dict | None = None,
    *,
    token: str | None = None,
    method: str = "POST",
) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read(65536)
            parsed = json.loads(body.decode("utf-8")) if body else {}
            return int(response.getcode() or 0), parsed
    except urllib.error.HTTPError as exc:
        body = exc.read(65536)
        try:
            parsed = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            parsed = {}
        return int(exc.code), parsed


def _admin_token() -> str:
    data = json.loads(os.environ["SYNAPSE_AUTH_TOKENS"])
    for token, record in data.items():
        if isinstance(record, dict) and record.get("role") == "admin":
            return str(token)
    raise RuntimeError("admin token missing")


def _stamp(seconds: int) -> str:
    instant = LAB_TIME + timedelta(seconds=seconds)
    return instant.strftime("%Y-%m-%dT%H:%M:%S.") + f"{instant.microsecond:06d}Z"


def _ingest(base: str, key, raw: dict) -> str:
    envelope = normalize_observation(raw)
    status, body = _http_json(
        f"{base}/api/v1/telemetry/ingest",
        {
            "envelope": envelope.model_dump(mode="json"),
            "signature": sign_event(key, envelope),
        },
    )
    if status not in {200, 201}:
        raise RuntimeError(f"synthetic ingest failed status={status}")
    return str(envelope.event_id)


def main() -> int:
    from synapse_agent.log import configure_logging, log_event

    configure_logging()
    _load_env()
    _ensure_api_environment()
    from alembic import command
    from alembic.config import Config

    if os.environ.get("MIGRATION_DATABASE_URL"):
        command.upgrade(Config(str(ROOT / "apps" / "api" / "alembic.ini")), "head")
    migration = os.environ.pop("MIGRATION_DATABASE_URL", None)
    from synapse_api.config import get_settings
    from synapse_api.db import reset_engine
    from synapse_api.main import create_app

    get_settings.cache_clear()
    reset_engine()
    app = create_app()
    import threading

    import uvicorn

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18081, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not server.started:
        time.sleep(0.05)
    if not server.started:
        return 1
    base = "http://127.0.0.1:18081"
    try:
        token = _admin_token()
        expiry = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        status, created = _http_json(
            f"{base}/api/v1/targets",
            {
                "name": "correlation-lab",
                "owner": "research-team",
                "scope": {
                    "environment": "lab",
                    "assets": ["correlation-lab.internal"],
                    "description": "Synthetic correlation demonstration target.",
                },
                "authorization_expiry": expiry,
                "allowed_capabilities": ["telemetry.ingest"],
            },
            token=token,
        )
        if status != 201:
            log_event("demo_target_failed", status=status)
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
        synthetic_ids: list[str] = []
        common = {
            "target_id": target_id,
            "agent_id": agent_id,
            "boot_id": boot_id,
        }
        synthetic_ids.append(
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
        )
        synthetic_ids.append(
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
        )
        synthetic_ids.append(
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
        )
        synthetic_ids.append(
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
        )
        sequence = 5
        for index in range(6):
            synthetic_ids.append(
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
            )
            sequence += 1
        synthetic_ids.append(
            _ingest(
                base,
                key,
                {
                    **common,
                    "event_type": "process_exited",
                    "sequence": sequence,
                    "observed_at": _stamp(20),
                    "pid": 300,
                    "start_ticks": 4,
                },
            )
        )
        run_status, run = _http_json(
            f"{base}/api/v1/targets/{target_id}/correlation/runs",
            {"window_seconds": 300},
            token=token,
        )
        if run_status != 201:
            log_event("demo_run_failed", status=run_status)
            return 1
        _findings_status, findings = _http_json(
            f"{base}/api/v1/targets/{target_id}/findings?limit=100",
            method="GET",
            token=token,
        )
        example = (findings.get("items") or [{}])[0]
        log_event(
            "demo_complete",
            dataset="synthetic_lab",
            note="constructed envelopes, not procfs samples",
            target_id=target_id,
            synthetic_event_count=len(synthetic_ids),
            risk_score=run.get("risk", {}).get("score"),
            formula=run.get("risk", {}).get("formula"),
            finding_count=run.get("finding_count"),
            example_type=example.get("finding_type"),
            example_epistemic=example.get("epistemic_status"),
            example_events=example.get("supporting_event_ids"),
            example_explanation=example.get("explanation"),
        )
        if run.get("risk", {}).get("score", 0) <= 0:
            return 1
        if not findings.get("items"):
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
