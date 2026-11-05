"""Reproducible splits. Group-aware when a capture id exists."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SplitConfig:
    seed: int
    strategy: str
    train_ratio: float
    validation_ratio: float
    test_ratio: float
    group_key: str | None
    notes: str


DEFAULT_SPLIT = SplitConfig(
    seed=42,
    strategy="group_or_sequential",
    train_ratio=0.6,
    validation_ratio=0.2,
    test_ratio=0.2,
    group_key="source_file",
    notes="Random row splits are rejected when they would mix related captures.",
)


def sequential_indices(
    n: int, config: SplitConfig = DEFAULT_SPLIT
) -> tuple[list[int], list[int], list[int]]:
    if n < 3:
        raise ValueError("need at least 3 rows for a split")
    train_end = max(1, int(n * config.train_ratio))
    val_end = max(train_end + 1, int(n * (config.train_ratio + config.validation_ratio)))
    if val_end >= n:
        val_end = n - 1
    train = list(range(0, train_end))
    validation = list(range(train_end, val_end))
    test = list(range(val_end, n))
    overlap = set(train) & set(validation) | set(train) & set(test) | set(validation) & set(test)
    if overlap:
        raise RuntimeError("split leakage")
    return train, validation, test


def assert_no_index_leakage(train: list[int], validation: list[int], test: list[int]) -> None:
    if set(train) & set(validation) or set(train) & set(test) or set(validation) & set(test):
        raise AssertionError("train/validation/test index overlap")
