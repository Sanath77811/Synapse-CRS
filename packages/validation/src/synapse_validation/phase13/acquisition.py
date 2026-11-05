"""Bounded acquisition. No multi-gigabyte downloads. No untrusted object dumps."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_SUFFIXES = {".json", ".jsonl", ".csv", ".txt", ".md"}
DMBD_LABEL_TRAIN = "https://gdo168.llnl.gov/data/dmbd/truth_labels_train.json"
DMBD_LABEL_TEST = "https://gdo168.llnl.gov/data/dmbd/truth_labels_test.json"
DMBD_INDEX = "https://gdo168.llnl.gov/data/dmbd/"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def head_content_length(url: str, timeout: int = 20) -> int | None:
    request = Request(url, method="HEAD")
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            length = response.headers.get("Content-Length")
            if length is None:
                return None
            return int(length)
    except Exception:
        return None


def download_bounded(
    url: str, dest: Path, *, max_bytes: int = MAX_DOWNLOAD_BYTES
) -> dict[str, object]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http(s) URLs are allowed")
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError(f"refusing suffix {suffix}")
    length = head_content_length(url)
    if length is None:
        raise ValueError("Content-Length required before download")
    if length > max_bytes:
        return {
            "downloaded": False,
            "url": url,
            "content_length": length,
            "reason": f"file exceeds max_bytes={max_bytes}",
        }
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, method="GET")
    with urlopen(request, timeout=60) as response, dest.open("wb") as handle:  # noqa: S310
        remaining = length
        while remaining > 0:
            chunk = response.read(min(65536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            handle.write(chunk)
    size = dest.stat().st_size
    if size > max_bytes:
        dest.unlink(missing_ok=True)
        raise ValueError("downloaded file exceeded bound")
    return {
        "downloaded": True,
        "url": url,
        "path": str(dest),
        "content_length": length,
        "sha256": sha256_file(dest),
        "acquired_at": datetime.now(UTC).isoformat(),
    }


def safe_extract_zip(
    archive: Path, dest: Path, *, max_total: int = MAX_DOWNLOAD_BYTES
) -> dict[str, object]:
    import zipfile

    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    if not zipfile.is_zipfile(archive):
        raise ValueError("not a zip archive")
    written = 0
    names = []
    with zipfile.ZipFile(archive) as zipped:
        for info in zipped.infolist():
            name = info.filename
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError(f"unsafe zip member {name}")
            target = (dest / name).resolve()
            if dest not in target.parents and target != dest:
                raise ValueError(f"zip path traversal {name}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            written += info.file_size
            if written > max_total:
                raise ValueError("extracted size exceeds bound")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(info) as source, target.open("wb") as out:
                out.write(source.read())
            names.append(name)
    return {"extracted": names, "bytes": written}


def load_json_object(path: Path, *, max_bytes: int = MAX_DOWNLOAD_BYTES) -> object:
    if path.stat().st_size > max_bytes:
        raise ValueError("JSON exceeds max_bytes")
    return json.loads(path.read_text(encoding="utf-8"))
