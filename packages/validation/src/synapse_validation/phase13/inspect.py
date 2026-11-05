"""Streaming inspection of JSONL endpoint evidence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

MAX_INSPECT_BYTES = 8 * 1024 * 1024


def inspect_jsonl(path: Path, *, max_rows: int = 5000) -> dict[str, object]:
    size = path.stat().st_size
    if size > MAX_INSPECT_BYTES:
        raise ValueError("file exceeds inspect bound")
    columns: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    types: Counter[str] = Counter()
    samples: set[str] = set()
    missing = 0
    rows = 0
    duplicates = 0
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if rows >= max_rows:
                break
            text = line.strip()
            if not text:
                continue
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                missing += 1
                continue
            if not isinstance(raw, dict):
                missing += 1
                continue
            rows += 1
            columns.update(raw.keys())
            sid = str(raw.get("sample_id", ""))
            rid = str(raw.get("source_record_id", ""))
            if rid in seen_ids:
                duplicates += 1
            elif rid:
                seen_ids.add(rid)
            if sid:
                samples.add(sid)
            if raw.get("label"):
                labels[str(raw["label"]).lower()] += 1
            types[str(raw.get("event_type", ""))] += 1
    return {
        "path": path.name,
        "file_size_bytes": size,
        "rows_inspected": rows,
        "columns": dict(columns),
        "label_counts": dict(labels),
        "event_types": dict(types),
        "sample_count": len(samples),
        "duplicate_source_record_ids": duplicates,
        "malformed_lines": missing,
        "process_id_fields_present": [
            name for name in ("pid_hash", "os_pid", "parent_pid_hash") if name in columns
        ],
    }
