"""Boot identity, monotonic sequence, and a bounded pending queue on disk."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from synapse_telemetry.envelope import UUID_V4_PATTERN, _parse_uuid_v4

from synapse_agent.log import log_event

KERNEL_BOOT_ID = Path("/proc/sys/kernel/random/boot_id")


class StateError(Exception):
    """Agent state could not be read or written safely."""


@dataclass
class PendingItem:
    envelope: dict[str, Any]
    signature: str
    attempts: int = 0


@dataclass
class AgentState:
    boot_id: UUID
    next_sequence: int
    pending: list[PendingItem]
    failed: list[PendingItem]


def state_path(home: Path) -> Path:
    return home / "state.json"


def read_kernel_boot_id() -> UUID | None:
    try:
        raw = KERNEL_BOOT_ID.read_text(encoding="ascii").strip()
    except OSError:
        return None
    try:
        if UUID_V4_PATTERN:
            return _parse_uuid_v4(raw)
    except ValueError:
        return None
    return None


def load_state(home: Path, *, max_pending: int) -> AgentState:
    path = state_path(home)
    kernel = read_kernel_boot_id()
    if not path.exists():
        boot = kernel or uuid4()
        state = AgentState(boot_id=boot, next_sequence=1, pending=[], failed=[])
        save_state(home, state, max_pending=max_pending)
        return state
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError("agent state file is invalid") from exc
    try:
        stored_boot = _parse_uuid_v4(str(raw["boot_id"]))
        next_sequence = int(raw["next_sequence"])
        pending = [_item(item) for item in raw.get("pending", [])]
        failed = [_item(item) for item in raw.get("failed", [])]
    except (KeyError, TypeError, ValueError) as exc:
        raise StateError("agent state file is invalid") from exc
    if next_sequence < 1:
        raise StateError("agent sequence is invalid")
    boot = kernel or stored_boot
    if kernel is not None and kernel != stored_boot:
        log_event("boot_changed", previous=str(stored_boot), current=str(kernel))
        next_sequence = 1
        boot = kernel
    if len(pending) > max_pending:
        raise StateError("pending queue exceeds the configured bound")
    return AgentState(boot_id=boot, next_sequence=next_sequence, pending=pending, failed=failed)


def allocate_sequence(state: AgentState) -> int:
    value = state.next_sequence
    state.next_sequence = value + 1
    return value


def save_state(home: Path, state: AgentState, *, max_pending: int, max_bytes: int = 524288) -> None:
    if len(state.pending) > max_pending:
        raise StateError("pending queue is full")
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    document = {
        "boot_id": str(state.boot_id),
        "next_sequence": state.next_sequence,
        "pending": [_dump(item) for item in state.pending],
        "failed": [_dump(item) for item in state.failed[-max_pending:]],
    }
    encoded = json.dumps(document, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(encoded) > max_bytes:
        raise StateError("agent state exceeds the configured size bound")
    path = state_path(home)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    os.chmod(path, 0o600)


def _item(raw: object) -> PendingItem:
    if not isinstance(raw, dict):
        raise ValueError("pending item is invalid")
    envelope = raw.get("envelope")
    signature = raw.get("signature")
    attempts = int(raw.get("attempts", 0))
    if not isinstance(envelope, dict) or not isinstance(signature, str):
        raise ValueError("pending item is invalid")
    if attempts < 0:
        raise ValueError("pending item is invalid")
    return PendingItem(envelope=envelope, signature=signature, attempts=attempts)


def _dump(item: PendingItem) -> dict[str, Any]:
    return {
        "envelope": item.envelope,
        "signature": item.signature,
        "attempts": item.attempts,
    }
