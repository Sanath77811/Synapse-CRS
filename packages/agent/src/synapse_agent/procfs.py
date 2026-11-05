"""Read process and network table snapshots from a procfs-style tree.

Polling is not a complete event log. A process that starts and exits between
two polls is missed. PID reuse is distinguished with start_ticks. Permission
errors skip that row. Root is not required; unreadable tasks are omitted.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from synapse_telemetry.envelope import PID_MAX, PORT_MAX, START_TICKS_MAX, UID_MAX

TCP_LISTEN = "0A"


@dataclass(frozen=True)
class ProcessSnapshot:
    pid: int
    ppid: int
    uid: int
    start_ticks: int
    comm: str

    @property
    def identity(self) -> tuple[int, int]:
        return (self.pid, self.start_ticks)


@dataclass(frozen=True)
class NetworkSnapshot:
    protocol: str
    local_port: int
    remote_port: int
    uid: int
    inode: int
    pid: int | None

    @property
    def identity(self) -> tuple[str, int, int, int, int]:
        return (self.protocol, self.local_port, self.remote_port, self.uid, self.inode)


class ProcfsSource:
    def __init__(self, root: Path) -> None:
        self.root = root

    def processes(self) -> dict[tuple[int, int], ProcessSnapshot]:
        found: dict[tuple[int, int], ProcessSnapshot] = {}
        try:
            entries = list(self.root.iterdir())
        except OSError:
            return found
        for entry in entries:
            name = entry.name
            if not name.isdigit():
                continue
            pid = int(name)
            if pid < 1 or pid > PID_MAX:
                continue
            snapshot = _read_process(entry, pid)
            if snapshot is None:
                continue
            found[snapshot.identity] = snapshot
        return found

    def networks(self) -> dict[tuple[str, int, int, int, int], NetworkSnapshot]:
        inodes = _socket_inodes(self.root)
        found: dict[tuple[str, int, int, int, int], NetworkSnapshot] = {}
        for protocol, filename in (
            ("tcp", "tcp"),
            ("tcp6", "tcp6"),
            ("udp", "udp"),
            ("udp6", "udp6"),
        ):
            path = self.root / "net" / filename
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line in lines[1:]:
                parsed = _parse_net_line(protocol, line, inodes)
                if parsed is None:
                    continue
                found[parsed.identity] = parsed
        return found


def _read_process(directory: Path, pid: int) -> ProcessSnapshot | None:
    try:
        stat_text = (directory / "stat").read_text(encoding="utf-8", errors="replace")
        status_text = (directory / "status").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    parsed = _parse_stat(stat_text)
    if parsed is None:
        return None
    comm, ppid, start_ticks = parsed
    uid = _parse_uid(status_text)
    if uid is None:
        return None
    if ppid < 0 or ppid > PID_MAX:
        return None
    if start_ticks < 0 or start_ticks > START_TICKS_MAX:
        return None
    if uid < 0 or uid > UID_MAX:
        return None
    return ProcessSnapshot(pid=pid, ppid=ppid, uid=uid, start_ticks=start_ticks, comm=comm)


def _parse_stat(text: str) -> tuple[str, int, int] | None:
    start = text.find("(")
    end = text.rfind(")")
    if start < 0 or end < 0 or end <= start:
        return None
    comm = text[start + 1 : end]
    rest = text[end + 1 :].split()
    if len(rest) < 20:
        return None
    try:
        ppid = int(rest[1])
        start_ticks = int(rest[19])
    except ValueError:
        return None
    return comm, ppid, start_ticks


def _parse_uid(status_text: str) -> int | None:
    for line in status_text.splitlines():
        if line.startswith("Uid:"):
            parts = line.split()
            if len(parts) < 2:
                return None
            try:
                return int(parts[1])
            except ValueError:
                return None
    return None


def _parse_net_line(protocol: str, line: str, inodes: dict[int, int]) -> NetworkSnapshot | None:
    parts = line.split()
    if len(parts) < 10:
        return None
    state = parts[3]
    if protocol in {"tcp", "tcp6"} and state == TCP_LISTEN:
        return None
    local_port = _hex_port(parts[1])
    remote_port = _hex_port(parts[2])
    if local_port is None or remote_port is None:
        return None
    try:
        uid = int(parts[7])
        inode = int(parts[9])
    except ValueError:
        return None
    if uid < 0 or uid > UID_MAX or inode < 0:
        return None
    pid = inodes.get(inode)
    return NetworkSnapshot(
        protocol=protocol,
        local_port=local_port,
        remote_port=remote_port,
        uid=uid,
        inode=inode,
        pid=pid,
    )


def _hex_port(address: str) -> int | None:
    if ":" not in address:
        return None
    _, port_hex = address.rsplit(":", 1)
    try:
        port = int(port_hex, 16)
    except ValueError:
        return None
    if port < 0 or port > PORT_MAX:
        return None
    return port


def _socket_inodes(root: Path) -> dict[int, int]:
    mapping: dict[int, int] = {}
    try:
        entries = list(root.iterdir())
    except OSError:
        return mapping
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid < 1 or pid > PID_MAX:
            continue
        fd_dir = entry / "fd"
        try:
            fds = list(fd_dir.iterdir())
        except OSError:
            continue
        for fd in fds:
            try:
                target = os.readlink(fd)
            except OSError:
                continue
            inode = _parse_socket_inode(target)
            if inode is not None:
                mapping[inode] = pid
    return mapping


def _parse_socket_inode(target: str) -> int | None:
    prefix = "socket:["
    if not target.startswith(prefix) or not target.endswith("]"):
        return None
    raw = target[len(prefix) : -1]
    try:
        value = int(raw)
    except ValueError:
        return None
    if value < 0:
        return None
    return value
