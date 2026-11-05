"""Turn procfs diffs into normalized, signed ingest items."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from synapse_telemetry.envelope import format_observed_at
from synapse_telemetry.normalization import NormalizationError, normalize_observation
from synapse_telemetry.signatures import SigningKey, sign_event

from synapse_agent.log import log_event
from synapse_agent.procfs import NetworkSnapshot, ProcessSnapshot, ProcfsSource
from synapse_agent.state import AgentState, PendingItem, allocate_sequence


class Collector:
    def __init__(
        self,
        source: ProcfsSource,
        *,
        agent_id: UUID,
        target_id: UUID,
        signing_key: SigningKey,
    ) -> None:
        self.source = source
        self.agent_id = agent_id
        self.target_id = target_id
        self.signing_key = signing_key
        self._processes: dict[tuple[int, int], ProcessSnapshot] | None = None
        self._networks: dict[tuple[str, int, int, int, int], NetworkSnapshot] | None = None

    def warm(self) -> None:
        self._processes = self.source.processes()
        self._networks = self.source.networks()
        log_event(
            "collector_warm",
            processes=len(self._processes),
            networks=len(self._networks),
        )

    def poll(self, state: AgentState) -> list[PendingItem]:
        if self._processes is None or self._networks is None:
            self.warm()
            return []
        current_processes = self.source.processes()
        current_networks = self.source.networks()
        started = [
            current_processes[key] for key in current_processes.keys() - self._processes.keys()
        ]
        exited = [self._processes[key] for key in self._processes.keys() - current_processes.keys()]
        connected = [
            current_networks[key] for key in current_networks.keys() - self._networks.keys()
        ]
        self._processes = current_processes
        self._networks = current_networks
        items: list[PendingItem] = []
        observed_at = format_observed_at(datetime.now(UTC))
        for process in started:
            item = self._item(
                state,
                {
                    "event_type": "process_started",
                    "pid": process.pid,
                    "ppid": process.ppid,
                    "uid": process.uid,
                    "start_ticks": process.start_ticks,
                    "comm": process.comm,
                    "observed_at": observed_at,
                },
            )
            if item is not None:
                items.append(item)
        for process in exited:
            item = self._item(
                state,
                {
                    "event_type": "process_exited",
                    "pid": process.pid,
                    "start_ticks": process.start_ticks,
                    "observed_at": observed_at,
                },
            )
            if item is not None:
                items.append(item)
        for conn in connected:
            item = self._item(
                state,
                {
                    "event_type": "network_connection_observed",
                    "protocol": conn.protocol,
                    "local_port": conn.local_port,
                    "remote_port": conn.remote_port,
                    "remote_address": "[ip]",
                    "uid": conn.uid,
                    "pid": conn.pid,
                    "observed_at": observed_at,
                },
            )
            if item is not None:
                items.append(item)
        return items

    def _item(self, state: AgentState, raw: dict[str, object]) -> PendingItem | None:
        sequence = allocate_sequence(state)
        raw.update(
            {
                "target_id": str(self.target_id),
                "agent_id": str(self.agent_id),
                "boot_id": str(state.boot_id),
                "sequence": sequence,
                "event_id": str(uuid4()),
            }
        )
        try:
            envelope = normalize_observation(raw)
        except NormalizationError:
            log_event("normalize_failed", event_type=str(raw.get("event_type")))
            return None
        signature = sign_event(self.signing_key, envelope)
        return PendingItem(
            envelope=envelope.model_dump(mode="json"),
            signature=signature,
        )
