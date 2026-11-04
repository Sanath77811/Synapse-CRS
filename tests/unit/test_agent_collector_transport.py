"""Collector diffs, signing, retry classification, and HTTP outcomes."""

import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from uuid import uuid4

from synapse_agent.collector import Collector
from synapse_agent.config import AgentConfig
from synapse_agent.procfs import ProcfsSource
from synapse_agent.runner import drain_pending
from synapse_agent.state import AgentState, PendingItem, allocate_sequence
from synapse_agent.transport import post_ingest
from synapse_telemetry.envelope import TelemetryEnvelope
from synapse_telemetry.signatures import generate_signing_key, verify_event

STAT_A = (
    "10 (worker) S 1 10 10 0 -1 4194304 0 0 0 0 0 0 0 0 20 0 1 0 "
    "50 0 0 0 0 0 0 0 0 0 0 0 0 17 0 0 0 0 0 0\n"
)
STAT_B = (
    "11 (worker) S 1 11 11 0 -1 4194304 0 0 0 0 0 0 0 0 20 0 1 0 "
    "60 0 0 0 0 0 0 0 0 0 0 0 0 17 0 0 0 0 0 0\n"
)
STATUS = "Uid:\t1000\t1000\t1000\t1000\n"


def _proc(root: Path, pids: dict[int, str]) -> None:
    for pid, stat in pids.items():
        directory = root / str(pid)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "stat").write_text(stat)
        (directory / "status").write_text(STATUS)
    (root / "net").mkdir(exist_ok=True)
    (root / "net" / "tcp").write_text(
        "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt"
        "   uid  timeout inode\n"
    )


def test_collector_emits_start_then_exit(tmp_path: Path) -> None:
    _proc(tmp_path, {10: STAT_A})
    key = generate_signing_key()
    agent_id = uuid4()
    target_id = uuid4()
    collector = Collector(
        ProcfsSource(tmp_path),
        agent_id=agent_id,
        target_id=target_id,
        signing_key=key,
    )
    state = AgentState(boot_id=uuid4(), next_sequence=1, pending=[], failed=[])
    assert collector.poll(state) == []
    _proc(tmp_path, {10: STAT_A, 11: STAT_B})
    started = collector.poll(state)
    assert len(started) == 1
    envelope = TelemetryEnvelope.model_validate(started[0].envelope)
    assert envelope.event_type == "process_started"
    assert envelope.payload.pid == 11
    verify_event(key.public_key(), envelope, started[0].signature)
    first_seq = envelope.sequence
    shutil.rmtree(tmp_path / "11")
    exited = collector.poll(state)
    assert len(exited) == 1
    exit_env = TelemetryEnvelope.model_validate(exited[0].envelope)
    assert exit_env.event_type == "process_exited"
    assert exit_env.payload.pid == 11
    assert exit_env.payload.start_ticks == 60
    assert exit_env.sequence == first_seq + 1
    allocate_sequence(state)
    assert state.next_sequence == exit_env.sequence + 2


class _Handler(BaseHTTPRequestHandler):
    responses: list[tuple[int, bytes]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        status, body = self.responses.pop(0)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _serve() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}/api/v1/telemetry/ingest"


def test_transport_classifies_http_outcomes() -> None:
    server, url = _serve()
    envelope = {"event_id": str(uuid4())}
    try:
        _Handler.responses = [(201, b'{"persistence_status":"stored"}')]
        ok = post_ingest(url, envelope, "sig", timeout=2)
        assert ok.kind == "accepted"
        _Handler.responses = [(200, b'{"persistence_status":"duplicate"}')]
        dup = post_ingest(url, envelope, "sig", timeout=2)
        assert dup.kind == "duplicate"
        _Handler.responses = [
            (401, b'{"error":{"code":"invalid_signature","message":"no","details":{}}}')
        ]
        denied = post_ingest(url, envelope, "sig", timeout=2)
        assert denied.kind == "permanent"
        assert denied.code == "invalid_signature"
        _Handler.responses = [(503, b"{}")]
        busy = post_ingest(url, envelope, "sig", timeout=2)
        assert busy.kind == "transient"
    finally:
        server.shutdown()


def test_drain_retries_transient_then_accepts(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_post(url, envelope, signature, timeout):
        calls["n"] += 1
        from synapse_agent.transport import TransportResult

        if calls["n"] == 1:
            return TransportResult(kind="transient", status_code=503, code=None)
        return TransportResult(kind="accepted", status_code=201, code=None)

    monkeypatch.setattr("synapse_agent.runner.post_ingest", fake_post)
    state = AgentState(
        boot_id=uuid4(),
        next_sequence=2,
        pending=[
            PendingItem(
                envelope={"sequence": 1, "event_type": "process_started"},
                signature="x",
            )
        ],
        failed=[],
    )
    settings = AgentConfig(
        agent_id=uuid4(),
        target_id=uuid4(),
        ingest_url="http://127.0.0.1:9/api/v1/telemetry/ingest",
        home_dir="/tmp",
        poll_seconds=1.0,
        max_pending=10,
        max_state_bytes=4096,
        http_timeout_seconds=1.0,
        proc_root="/proc",
    )
    assert drain_pending(state, settings) is False
    assert len(state.pending) == 1
    assert drain_pending(state, settings) is True
    assert state.pending == []
