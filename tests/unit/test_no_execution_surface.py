"""v0.1 source does not grow a command-execution API."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = [
    ROOT / "apps" / "api" / "src",
    ROOT / "packages",
    ROOT / "agent",
]
FORBIDDEN = ("subprocess", "os.system", "os.popen", "shell=True", "socket.socket")


def test_foundation_source_has_no_shell_or_socket_client() -> None:
    offenders: list[str] = []
    for root in SCAN_ROOTS:
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".md"} or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for token in FORBIDDEN:
                if token in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {token}")
    assert offenders == []
