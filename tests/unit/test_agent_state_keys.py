"""Key file modes and sequence persistence."""

from pathlib import Path
from uuid import uuid4

import pytest
from synapse_agent.keys import KeyStoreError, load_or_create_signing_key
from synapse_agent.state import (
    PendingItem,
    allocate_sequence,
    load_state,
    save_state,
    state_path,
)
from synapse_telemetry.signatures import public_key_fingerprint


def test_private_key_file_is_owner_read_write_only(tmp_path: Path) -> None:
    key = load_or_create_signing_key(tmp_path)
    pem = tmp_path / "ed25519.pem"
    assert pem.exists()
    assert pem.stat().st_mode & 0o777 == 0o600
    again = load_or_create_signing_key(tmp_path)
    assert public_key_fingerprint(key.public_key()) == public_key_fingerprint(again.public_key())
    pem.chmod(0o644)
    with pytest.raises(KeyStoreError):
        load_or_create_signing_key(tmp_path)


def test_sequence_does_not_reuse_after_reload(tmp_path: Path) -> None:
    state = load_state(tmp_path, max_pending=10)
    first = allocate_sequence(state)
    second = allocate_sequence(state)
    save_state(tmp_path, state, max_pending=10)
    loaded = load_state(tmp_path, max_pending=10)
    third = allocate_sequence(loaded)
    assert first == 1
    assert second == 2
    assert third == 3
    assert first != second
    mode = state_path(tmp_path).stat().st_mode & 0o777
    assert mode == 0o600


def test_pending_queue_bound(tmp_path: Path) -> None:
    from synapse_agent.state import StateError

    state = load_state(tmp_path, max_pending=2)
    item = PendingItem(envelope={"event_id": str(uuid4())}, signature="A" * 88)
    state.pending = [item, item, item]
    with pytest.raises(StateError):
        save_state(tmp_path, state, max_pending=2)
