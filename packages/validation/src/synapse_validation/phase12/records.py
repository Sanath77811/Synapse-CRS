"""Normalized endpoint evidence. Unknown fields stay unknown."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Provenance = Literal["observed", "derived", "inferred", "unavailable"]
LabelScope = Literal["sample", "process", "event", "host", "trace", "unknown"]


@dataclass(frozen=True)
class Field:
    value: object
    provenance: Provenance

    def as_dict(self) -> dict[str, object]:
        return {"value": self.value, "provenance": self.provenance}


def observed(value: object) -> Field:
    return Field(value, "observed")


def derived(value: object) -> Field:
    return Field(value, "derived")


def unavailable() -> Field:
    return Field(None, "unavailable")


@dataclass(frozen=True)
class EndpointRecord:
    source_dataset: str
    source_dataset_version: str
    source_file_id: str
    source_record_id: str
    source_sample_id: str
    source_host_id: Field
    source_process_id: Field
    source_parent_process_id: Field
    os_pid: Field
    parent_os_pid: Field
    event_type: str
    event_timestamp: Field
    process_start_timestamp: Field
    process_end_timestamp: Field
    network_connection_reference: Field
    label: Field
    label_scope: LabelScope
    label_source: str
    split: str
    raw: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        for name in (
            "source_host_id",
            "source_process_id",
            "source_parent_process_id",
            "os_pid",
            "parent_os_pid",
            "event_timestamp",
            "process_start_timestamp",
            "process_end_timestamp",
            "network_connection_reference",
            "label",
        ):
            payload[name] = getattr(self, name).as_dict()
        return payload
