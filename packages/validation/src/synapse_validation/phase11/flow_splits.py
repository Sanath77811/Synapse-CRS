"""Temporal or sequential splits with leakage checks. Fit nothing on test."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from synapse_validation.phase11.flow_loader import FlowRecord
from synapse_validation.splits import DEFAULT_SPLIT, sequential_indices


@dataclass(frozen=True)
class FlowSplit:
    strategy: str
    seed: int
    train_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    train_labels: dict[str, int]
    validation_labels: dict[str, int]
    test_labels: dict[str, int]
    classes_missing_from_test: tuple[str, ...]
    duplicate_signature_leakage: int
    notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _counts(records: list[FlowRecord]) -> dict[str, int]:
    tallies: dict[str, int] = {}
    for item in records:
        tallies[item.original_label] = tallies.get(item.original_label, 0) + 1
    return tallies


def _signature(record: FlowRecord) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, record.fields[key]) for key in record.fields if key != "Timestamp"))


def split_records(
    records: tuple[FlowRecord, ...],
) -> tuple[FlowSplit, list[int], list[int], list[int]]:
    if len(records) < 6:
        raise ValueError("need at least 6 flow records for a split")
    has_time = all(item.timestamp_raw for item in records)
    ordered = list(range(len(records)))
    if has_time:
        ordered.sort(key=lambda index: (records[index].timestamp_raw, records[index].line_number))
        strategy = "temporal_then_sequential"
        notes = "Ordered by Timestamp then line number. No random row shuffle."
    else:
        strategy = "sequential_file_order"
        notes = "No Timestamp column; sequential file order is used instead of a random split."
    n = len(ordered)
    train_pos, val_pos, test_pos = sequential_indices(n, DEFAULT_SPLIT)
    train_idx = [ordered[position] for position in train_pos]
    val_idx = [ordered[position] for position in val_pos]
    test_idx = [ordered[position] for position in test_pos]
    train = [records[i] for i in train_idx]
    validation = [records[i] for i in val_idx]
    test = [records[i] for i in test_idx]
    train_sigs = {_signature(item) for item in train}
    val_sigs = {_signature(item) for item in validation}
    test_sigs = {_signature(item) for item in test}
    leakage = len(train_sigs & test_sigs) + len(train_sigs & val_sigs) + len(val_sigs & test_sigs)
    all_labels = set(_counts(list(records)))
    missing_test = tuple(sorted(all_labels - set(_counts(test))))
    split = FlowSplit(
        strategy=strategy,
        seed=DEFAULT_SPLIT.seed,
        train_ids=tuple(item.source_row_id for item in train),
        validation_ids=tuple(item.source_row_id for item in validation),
        test_ids=tuple(item.source_row_id for item in test),
        train_labels=_counts(train),
        validation_labels=_counts(validation),
        test_labels=_counts(test),
        classes_missing_from_test=missing_test,
        duplicate_signature_leakage=leakage,
        notes=notes,
    )
    return split, train_idx, val_idx, test_idx
