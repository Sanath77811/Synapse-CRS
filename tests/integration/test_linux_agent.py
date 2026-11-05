"""Linux agent delivers enrolled telemetry to a live ingest HTTP server."""

import time
from pathlib import Path
from threading import Thread
from uuid import UUID, uuid4

import uvicorn
from sqlalchemy import create_engine, text
from synapse_agent.config import AgentConfig
from synapse_agent.keys import load_or_create_signing_key
from synapse_agent.runner import drain_pending, prepare_runtime
from synapse_agent.state import save_state
from synapse_telemetry.signatures import generate_signing_key, public_key_fingerprint

from tests.integration.helpers import auth, target_payload
from tests.integration.test_agent_enrollment import _enroll

STAT = (
    "4242 (python3) S 1 4242 4242 0 -1 4194304 0 0 0 0 0 0 0 0 20 0 1 0 "
    "77 0 0 0 0 0 0 0 0 0 0 0 0 17 0 0 0 0 0 0\n"
)
STATUS = "Uid:\t1000\t1000\t1000\t1000\n"


def _start_server(app) -> tuple[uvicorn.Server, str, Thread]:
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="error")
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not server.started:
        time.sleep(0.02)
    assert server.started
    sock = server.servers[0].sockets[0]
    port = sock.getsockname()[1]
    return server, f"http://127.0.0.1:{port}", thread


def test_enrolled_agent_delivers_procfs_event(client, tokens, tmp_path: Path) -> None:
    server, base, thread = _start_server(client.app)
    try:
        created = client.post(
            "/api/v1/targets",
            headers=auth(tokens["admin"]),
            json=target_payload(name="linux-agent-it"),
        )
        assert created.status_code == 201
        target_id = created.json()["id"]
        key = load_or_create_signing_key(tmp_path)
        agent_id = str(uuid4())
        enrolled = _enroll(client, tokens, target_id, key.public_key().raw_bytes().hex(), agent_id)
        assert enrolled.status_code == 201
        proc = tmp_path / "proc"
        proc.mkdir()
        (proc / "net").mkdir()
        (proc / "net" / "tcp").write_text(
            "  sl  local_address rem_address   st tx_queue rx_queue tr "
            "tm->when retrnsmt   uid  timeout inode\n"
        )
        config = AgentConfig(
            agent_id=UUID(agent_id),
            target_id=UUID(target_id),
            ingest_url=f"{base}/api/v1/telemetry/ingest",
            home_dir=str(tmp_path),
            poll_seconds=0.05,
            max_pending=20,
            max_state_bytes=65536,
            http_timeout_seconds=5.0,
            proc_root=str(proc),
        )
        collector, state, _home = prepare_runtime(config)
        process_dir = proc / "4242"
        process_dir.mkdir()
        (process_dir / "stat").write_text(STAT)
        (process_dir / "status").write_text(STATUS)
        produced = collector.poll(state)
        assert produced
        assert produced[0].envelope["event_type"] == "process_started"
        state.pending.extend(produced)
        save_state(
            tmp_path, state, max_pending=config.max_pending, max_bytes=config.max_state_bytes
        )
        assert drain_pending(state, config) is True
        engine = create_engine(tokens["app_url"])
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT event_type, identity_status, signature_verified, public_key_fingerprint
                    FROM telemetry_events
                    WHERE agent_id = :agent_id
                    """
                ),
                {"agent_id": agent_id},
            ).one()
        engine.dispose()
        assert row[0] == "process_started"
        assert row[1] == "enrolled"
        assert row[2] is True
        assert row[3] == public_key_fingerprint(key.public_key())
        stranger = generate_signing_key()
        assert stranger.public_key().raw_bytes().hex() != key.public_key().raw_bytes().hex()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
