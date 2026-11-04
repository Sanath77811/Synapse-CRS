"""Local Ed25519 key file. Permission bits are not hardware isolation."""

import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)
from synapse_telemetry.signatures import SigningKey

from synapse_agent.log import log_event


class KeyStoreError(Exception):
    """The private key file could not be created or loaded."""


def key_path(home: Path) -> Path:
    return home / "ed25519.pem"


def load_or_create_signing_key(home: Path) -> SigningKey:
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(home, 0o700)
    path = key_path(home)
    if path.exists():
        return _load(path)
    private = Ed25519PrivateKey.generate()
    pem = private.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, pem)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)
    log_event("key_created", path=str(path), mode="0600")
    return SigningKey(private)


def _load(path: Path) -> SigningKey:
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise KeyStoreError("private key file mode must not be group- or world-accessible")
    loaded = load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(loaded, Ed25519PrivateKey):
        raise KeyStoreError("private key file is not Ed25519")
    return SigningKey(loaded)
