"""Procfs snapshots from a fake tree and from live Linux /proc when present."""

import os
from pathlib import Path

from synapse_agent.procfs import ProcfsSource, _parse_stat

STAT = (
    "42 (python3) S 1 42 42 0 -1 4194304 0 0 0 0 0 0 0 0 20 0 1 0 "
    "123456 0 0 0 0 0 0 0 0 0 0 0 0 17 0 0 0 0 0 0\n"
)
STATUS = "Name:\tpython3\nUid:\t1000\t1000\t1000\t1000\n"
TCP = (
    "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt"
    "   uid  timeout inode\n"
    "   0: 0100007F:0050 0100007F:C384 01 00000000:00000000 00:00000000 00000000"
    "  1000        0 111 1 00000000 20 0 0 10 -1\n"
    "   1: 00000000:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000"
    "     0        0 222 1 00000000 100 0 0 10 0\n"
)


def _write_process(root: Path, pid: int, stat: str, status: str) -> None:
    directory = root / str(pid)
    directory.mkdir(parents=True)
    (directory / "stat").write_text(stat)
    (directory / "status").write_text(status)


def test_parse_stat_uses_comm_and_start_ticks() -> None:
    parsed = _parse_stat("9 (py thon) R 8 9 9 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 99 0")
    assert parsed is not None
    comm, ppid, start_ticks = parsed
    assert comm == "py thon"
    assert ppid == 8
    assert start_ticks == 99


def test_fake_procfs_diffs_processes_and_skips_listen(tmp_path: Path) -> None:
    _write_process(tmp_path, 42, STAT, STATUS)
    net = tmp_path / "net"
    net.mkdir()
    (net / "tcp").write_text(TCP)
    fd = tmp_path / "42" / "fd"
    fd.mkdir()
    (fd / "3").symlink_to("socket:[111]")
    source = ProcfsSource(tmp_path)
    processes = source.processes()
    assert (42, 123456) in processes
    assert processes[(42, 123456)].comm == "python3"
    networks = source.networks()
    assert any(item.local_port == 80 and item.remote_port == 50052 for item in networks.values())
    assert all(item.local_port != 8080 for item in networks.values())
    connected = next(iter(networks.values()))
    assert connected.pid == 42
    assert connected.protocol == "tcp"


def test_live_procfs_includes_this_process() -> None:
    if not Path("/proc/self/stat").exists():
        return
    source = ProcfsSource(Path("/proc"))
    processes = source.processes()
    self_pid = os.getpid()
    matches = [item for item in processes.values() if item.pid == self_pid]
    assert matches
    assert matches[0].start_ticks >= 0
