"""Sample-grouped splits. Events from one sample never cross the cut."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from synapse_validation.phase12.records import EndpointRecord


@dataclass(frozen=True)
class SampleSplit:
    strategy: str
    seed: int
    train_samples: tuple[str, ...]
    validation_samples: tuple[str, ...]
    test_samples: tuple[str, ...]
    train_labels: dict[str, int]
    validation_labels: dict[str, int]
    test_labels: dict[str, int]
    notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _sample_label(records: list[EndpointRecord]) -> str:
    values = [str(item.label.value) for item in records if item.label.value]
    return values[0] if values else "unknown"


def split_samples(records: tuple[EndpointRecord, ...]) -> SampleSplit:
    grouped: dict[str, list[EndpointRecord]] = defaultdict(list)
    for item in records:
        grouped[item.source_sample_id].append(item)
    official = {item.split for item in records if item.split in {"train", "validation", "test"}}
    if official == {"train", "validation", "test"} or official == {"train", "test"}:
        train = sorted(sid for sid, rows in grouped.items() if rows[0].split == "train")
        validation = sorted(sid for sid, rows in grouped.items() if rows[0].split == "validation")
        test = sorted(sid for sid, rows in grouped.items() if rows[0].split == "test")
        if not validation and train:
            validation = train[-max(1, len(train) // 5) :]
            train = [item for item in train if item not in set(validation)]
        strategy = "official_sample_split"
        notes = "Preserved source split field at sample granularity."
    else:
        names = sorted(grouped)
        n = len(names)
        train_n = max(1, int(n * 0.6))
        val_n = max(1, int(n * 0.2))
        train = names[:train_n]
        validation = names[train_n : train_n + val_n]
        test = names[train_n + val_n :] or names[-1:]
        strategy = "grouped_by_sample_id_sorted"
        notes = "No official split; samples sorted by id. Not a random event split."
    overlap = set(train) & set(validation) | set(train) & set(test) | set(validation) & set(test)
    if overlap:
        raise RuntimeError("sample split leakage")

    def counts(ids: list[str]) -> dict[str, int]:
        tallies: dict[str, int] = {}
        for sid in ids:
            label = _sample_label(grouped[sid])
            tallies[label] = tallies.get(label, 0) + 1
        return tallies

    return SampleSplit(
        strategy=strategy,
        seed=42,
        train_samples=tuple(train),
        validation_samples=tuple(validation),
        test_samples=tuple(test),
        train_labels=counts(train),
        validation_labels=counts(validation),
        test_labels=counts(test),
        notes=notes,
    )
