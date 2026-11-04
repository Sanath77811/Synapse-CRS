"""Isolated end-to-end demonstration of the Linux collector.

Starts the existing API in-process, enrolls an agent with the administrator
workflow, polls procfs, delivers signed events, then shows tamper and
unknown-agent rejection.
"""

from __future__ import annotations

import json
import os
import secrets
import signal
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from synapse_telemetry.signatures import generate_signing_key, public_key_fingerprint, sign_event

from synapse_agent.keys import load_or_create_signing_key
from synapse_agent.log import configure_logging, log_event
from synapse_agent.runner import drain_pending, prepare_runtime
from synapse_agent.state import save_state
from synapse_agent.transport import post_ingest

ROOT = Path(__file__).resolve().parents[4]


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
        raise RuntimeError(
            "DATABASE_URL or MIGRATION_DATABASE_URL and SYNAPSE_APP_PASSWORD are required"
        )
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
        with urllib.request.urlopen(request, timeout=10) as response:
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
    raw = os.environ.get("SYNAPSE_AUTH_TOKENS", "")
    data = json.loads(raw)
    for token, record in data.items():
        if isinstance(record, dict) and record.get("role") == "admin":
            return str(token)
    raise RuntimeError("an admin token is required for enrollment")


def _spawn_child() -> int:
    return int(os.spawnvp(os.P_NOWAIT, "python3", ["python3", "-c", "import time; time.sleep(30)"]))


def _wait_ready(base: str) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            status, payload = _http_json(f"{base}/ready", method="GET")
        except urllib.error.URLError:
            time.sleep(0.1)
            continue
        if status == 200 and payload.get("database") == "ok":
            return
        time.sleep(0.1)
    raise RuntimeError("API readiness timed out")


def main() -> int:
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
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=18080, log_level="error")
    server = uvicorn.Server(config)
    import threading

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not server.started:
        time.sleep(0.05)
    if not server.started:
        log_event("demo_api_start_failed")
        return 1
    base = "http://127.0.0.1:18080"
    try:
        _wait_ready(base)
        token = _admin_token()
        expiry = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        created_status, created = _http_json(
            f"{base}/api/v1/targets",
            {
                "name": "linux-agent-demo",
                "owner": "research-team",
                "scope": {
                    "environment": "lab",
                    "assets": ["linux-agent-demo.internal"],
                    "description": "Isolated collector demonstration target.",
                },
                "authorization_expiry": expiry,
                "allowed_capabilities": ["telemetry.ingest"],
            },
            token=token,
        )
        if created_status != 201:
            log_event("demo_target_failed", status=created_status)
            return 1
        target_id = created["id"]
        home = Path(os.environ.get("TMPDIR", "/tmp")) / f"synapse-agent-demo-{uuid4()}"
        key = load_or_create_signing_key(home)
        agent_id = str(uuid4())
        enrolled_status, enrolled = _http_json(
            f"{base}/api/v1/targets/{target_id}/agents",
            {"public_key_hex": key.public_key().raw_bytes().hex(), "agent_id": agent_id},
            token=token,
        )
        if enrolled_status != 201:
            log_event("demo_enroll_failed", status=enrolled_status)
            return 1
        os.environ["SYNAPSE_AGENT_ID"] = agent_id
        os.environ["SYNAPSE_TARGET_ID"] = target_id
        os.environ["SYNAPSE_AGENT_HOME"] = str(home)
        os.environ["SYNAPSE_INGEST_URL"] = f"{base}/api/v1/telemetry/ingest"
        os.environ["SYNAPSE_AGENT_POLL_SECONDS"] = "0.2"
        os.environ["SYNAPSE_AGENT_PROC_ROOT"] = "/proc"
        from synapse_agent.config import load_config

        settings = load_config()
        collector, state, home = prepare_runtime(settings)
        child = _spawn_child()
        _http_json(f"{base}/health", method="GET")
        time.sleep(0.4)
        produced = collector.poll(state)
        for item in produced:
            if len(state.pending) >= settings.max_pending:
                break
            state.pending.append(item)
        save_state(
            home, state, max_pending=settings.max_pending, max_bytes=settings.max_state_bytes
        )
        drain_pending(state, settings)
        save_state(
            home, state, max_pending=settings.max_pending, max_bytes=settings.max_state_bytes
        )
        os.kill(child, signal.SIGTERM)
        try:
            os.waitpid(child, 0)
        except ChildProcessError:
            pass
        time.sleep(0.4)
        produced = collector.poll(state)
        for item in produced:
            if len(state.pending) >= settings.max_pending:
                break
            state.pending.append(item)
        save_state(
            home, state, max_pending=settings.max_pending, max_bytes=settings.max_state_bytes
        )
        drain_pending(state, settings)
        save_state(
            home, state, max_pending=settings.max_pending, max_bytes=settings.max_state_bytes
        )
        engine = create_engine(os.environ["DATABASE_URL"])
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT event_type, identity_status, signature_verified, count(*)
                    FROM telemetry_events
                    WHERE agent_id = :agent_id
                    GROUP BY 1, 2, 3
                    ORDER BY 1
                    """
                ),
                {"agent_id": agent_id},
            ).all()
        engine.dispose()
        accepted = {str(row[0]): int(row[3]) for row in rows}
        if not rows or any(row[1] != "enrolled" or row[2] is not True for row in rows):
            log_event("demo_evidence_missing", rows=len(rows))
            return 1
        from synapse_telemetry.normalization import normalize_observation

        sample = normalize_observation(
            {
                "event_type": "process_started",
                "target_id": target_id,
                "agent_id": agent_id,
                "boot_id": str(state.boot_id),
                "sequence": 10_000,
                "pid": 4242,
                "ppid": 1,
                "uid": 1000,
                "start_ticks": 1,
                "comm": "python3",
            }
        )
        good_sig = sign_event(key, sample)
        tampered = ("A" if good_sig[0] != "A" else "B") + good_sig[1:]
        tamper = post_ingest(
            settings.ingest_url,
            sample.model_dump(mode="json"),
            tampered,
            timeout=5,
        )
        other = generate_signing_key()
        unknown = normalize_observation(
            {
                "event_type": "process_started",
                "target_id": target_id,
                "agent_id": str(uuid4()),
                "boot_id": str(uuid4()),
                "sequence": 1,
                "pid": 7,
                "ppid": 1,
                "uid": 1000,
                "start_ticks": 1,
                "comm": "python3",
            }
        )
        unknown_result = post_ingest(
            settings.ingest_url,
            unknown.model_dump(mode="json"),
            sign_event(other, unknown),
            timeout=5,
        )
        log_event(
            "demo_complete",
            target_id=target_id,
            agent_id=agent_id,
            fingerprint=public_key_fingerprint(key.public_key()),
            accepted=accepted,
            tamper_status=tamper.status_code,
            unknown_status=unknown_result.status_code,
            pending=len(state.pending),
        )
        if tamper.status_code != 401 or unknown_result.status_code != 403:
            return 1
        if "process_started" not in accepted:
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
