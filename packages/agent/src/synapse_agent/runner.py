"""Poll, enqueue, and drain with bounded backoff. Observer only."""

import signal
import time
from pathlib import Path

from synapse_agent.collector import Collector
from synapse_agent.config import AgentConfig, load_config
from synapse_agent.keys import load_or_create_signing_key
from synapse_agent.log import configure_logging, log_event
from synapse_agent.procfs import ProcfsSource
from synapse_agent.state import (
    AgentState,
    PendingItem,
    StateError,
    load_state,
    save_state,
)
from synapse_agent.transport import post_ingest

_STOP = False
MAX_ATTEMPTS = 8


def _handle_stop(_signum: int, _frame: object) -> None:
    global _STOP
    _STOP = True
    log_event("shutdown_requested")


def prepare_runtime(config: AgentConfig) -> tuple[Collector, AgentState, Path]:
    home = Path(config.home_dir)
    key = load_or_create_signing_key(home)
    state = load_state(home, max_pending=config.max_pending)
    collector = Collector(
        ProcfsSource(Path(config.proc_root)),
        agent_id=config.agent_id,
        target_id=config.target_id,
        signing_key=key,
    )
    collector.warm()
    save_state(
        home,
        state,
        max_pending=config.max_pending,
        max_bytes=config.max_state_bytes,
    )
    return collector, state, home


def run_cycles(config: AgentConfig, cycles: int, *, pause: float | None = None) -> AgentState:
    collector, state, home = prepare_runtime(config)
    interval = config.poll_seconds if pause is None else pause
    for _ in range(max(cycles, 0)):
        produced = collector.poll(state)
        for item in produced:
            _enqueue(state, item, config.max_pending)
        save_state(home, state, max_pending=config.max_pending, max_bytes=config.max_state_bytes)
        drain_pending(state, config)
        save_state(home, state, max_pending=config.max_pending, max_bytes=config.max_state_bytes)
        time.sleep(interval)
    return state


def run_forever(config: AgentConfig | None = None) -> None:
    configure_logging()
    settings = config or load_config()
    collector, state, home = prepare_runtime(settings)
    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)
    log_event(
        "agent_started",
        agent_id=str(settings.agent_id),
        target_id=str(settings.target_id),
        boot_id=str(state.boot_id),
    )
    backoff = 0.5
    while not _STOP:
        try:
            produced = collector.poll(state)
            for item in produced:
                _enqueue(state, item, settings.max_pending)
            save_state(
                home,
                state,
                max_pending=settings.max_pending,
                max_bytes=settings.max_state_bytes,
            )
            drained = drain_pending(state, settings)
            save_state(
                home,
                state,
                max_pending=settings.max_pending,
                max_bytes=settings.max_state_bytes,
            )
            if drained:
                backoff = 0.5
            elif state.pending:
                time.sleep(min(backoff, 8.0))
                backoff = min(backoff * 2, 8.0)
            time.sleep(settings.poll_seconds)
        except StateError:
            log_event("state_bound_reached")
            time.sleep(min(backoff, 8.0))
            backoff = min(backoff * 2, 8.0)
    log_event("agent_stopped", pending=len(state.pending))


def drain_pending(state: AgentState, settings: AgentConfig) -> bool:
    """Send queued items. Returns True when at least one item was accepted."""
    accepted = False
    remaining: list[PendingItem] = []
    for item in state.pending:
        result = post_ingest(
            settings.ingest_url,
            item.envelope,
            item.signature,
            timeout=settings.http_timeout_seconds,
        )
        if result.kind in {"accepted", "duplicate"}:
            accepted = True
            continue
        if result.kind == "permanent" or item.attempts + 1 >= MAX_ATTEMPTS:
            item.attempts += 1
            state.failed.append(item)
            log_event(
                "ingest_failed_permanent",
                status=result.status_code,
                code=result.code,
                sequence=item.envelope.get("sequence"),
            )
            continue
        item.attempts += 1
        remaining.append(item)
    state.pending = remaining
    if len(state.failed) > settings.max_pending:
        dropped = len(state.failed) - settings.max_pending
        state.failed = state.failed[-settings.max_pending :]
        log_event("failed_queue_trimmed", dropped=dropped)
    return accepted


def _enqueue(state: AgentState, item: PendingItem, max_pending: int) -> None:
    if len(state.pending) >= max_pending:
        raise StateError("pending queue is full")
    state.pending.append(item)
    log_event(
        "queued",
        event_type=item.envelope.get("event_type"),
        sequence=item.envelope.get("sequence"),
    )
