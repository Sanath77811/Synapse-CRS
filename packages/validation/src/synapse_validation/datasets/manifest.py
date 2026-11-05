from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DatasetManifest:
    name: str
    version: str
    source: str
    path: str
    sha256: str
    row_count: int
    excluded_count: int
    label_counts: dict[str, int]
    category_counts: dict[str, int]
    preprocessing: dict[str, object]
    available: bool
    notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
