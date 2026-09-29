"""Ed25519 signatures over the canonical telemetry envelope.

The private key stays on the agent. This module can generate one in memory
and sign with it. It does not store keys, enroll agents, or decide whether
a target is authorized. A valid signature proves only that the matching
private key produced it.

Signed bytes are the fixed domain prefix plus the canonical envelope.
The signature itself is not a field of the Phase 1 envelope.
"""

import base64
import re
from collections.abc import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from synapse_telemetry.canonical import canonical_event_bytes
from synapse_telemetry.envelope import TelemetryEnvelope

SIGNATURE_DOMAIN = b"synapse-crs/telemetry-signature/1\n"
PUBLIC_KEY_LENGTH = 32
SIGNATURE_LENGTH = 64
SIGNATURE_PATTERN = r"^[A-Za-z0-9+/]{86}==$"

_SIGNATURE_TEXT = re.compile(SIGNATURE_PATTERN)


class SignatureError(Exception):
    """A signature or verification key could not be accepted.

    Messages are fixed. They do not include keys, signatures, or event bodies.
    """


class SigningKey:
    """In-memory Ed25519 private key. There is no export method."""

    __slots__ = ("_private",)

    def __init__(self, private: Ed25519PrivateKey) -> None:
        if not isinstance(private, Ed25519PrivateKey):
            raise TypeError("signing requires an Ed25519 private key")
        self._private = private

    def __repr__(self) -> str:
        return "SigningKey(redacted)"

    def __str__(self) -> str:
        return "SigningKey(redacted)"

    @classmethod
    def generate(cls) -> "SigningKey":
        return cls(Ed25519PrivateKey.generate())

    def public_key(self) -> "VerificationKey":
        return VerificationKey(self._private.public_key())


class VerificationKey:
    """Ed25519 public key bytes. Enrollment does not happen here."""

    __slots__ = ("_public",)

    def __init__(self, public: Ed25519PublicKey) -> None:
        if not isinstance(public, Ed25519PublicKey):
            raise TypeError("verification requires an Ed25519 public key")
        self._public = public

    def __repr__(self) -> str:
        return "VerificationKey(redacted)"

    def raw_bytes(self) -> bytes:
        return self._public.public_bytes(Encoding.Raw, PublicFormat.Raw)

    @classmethod
    def from_raw_bytes(cls, raw: bytes) -> "VerificationKey":
        if not isinstance(raw, bytes) or len(raw) != PUBLIC_KEY_LENGTH:
            raise SignatureError("telemetry verification key is invalid")
        try:
            public = Ed25519PublicKey.from_public_bytes(raw)
        except ValueError:
            raise SignatureError("telemetry verification key is invalid") from None
        return cls(public)


def generate_signing_key() -> SigningKey:
    """Generate a new in-memory Ed25519 signing key."""
    return SigningKey.generate()


def signing_message(event: TelemetryEnvelope) -> bytes:
    """Return the exact bytes that Ed25519 signs."""
    if not isinstance(event, TelemetryEnvelope):
        raise TypeError("event must be a telemetry envelope")
    return SIGNATURE_DOMAIN + canonical_event_bytes(event)


def sign_event(key: SigningKey, event: TelemetryEnvelope | Mapping[str, object]) -> str:
    """Validate an envelope and return its standard-base64 Ed25519 signature."""
    if not isinstance(key, SigningKey):
        raise TypeError("sign_event requires a signing key")
    envelope = _require_envelope(event)
    return encode_signature(key._private.sign(signing_message(envelope)))


def verify_event(
    key: VerificationKey,
    event: TelemetryEnvelope | Mapping[str, object],
    signature: str,
) -> None:
    """Recreate the signed bytes and require a matching Ed25519 signature.

    Returns nothing when the signature is valid. Invalid signatures raise
    ``SignatureError`` and are never reported as valid.
    """
    if not isinstance(key, VerificationKey):
        raise TypeError("verify_event requires a verification key")
    envelope = _require_envelope(event)
    raw = decode_signature(signature)
    try:
        key._public.verify(raw, signing_message(envelope))
    except InvalidSignature:
        raise SignatureError("telemetry signature is invalid") from None


def encode_signature(raw: bytes) -> str:
    """Encode a 64-byte Ed25519 signature as standard base64 with padding."""
    if not isinstance(raw, bytes) or len(raw) != SIGNATURE_LENGTH:
        raise SignatureError("telemetry signature encoding is invalid")
    text = base64.standard_b64encode(raw).decode("ascii")
    if _SIGNATURE_TEXT.fullmatch(text) is None:
        raise SignatureError("telemetry signature encoding is invalid")
    return text


def decode_signature(signature: str) -> bytes:
    """Decode standard base64 into exactly 64 signature bytes.

    URL-safe base64, missing padding, whitespace, and any other length are
    rejected. Raw signature bytes are not accepted.
    """
    if not isinstance(signature, str) or _SIGNATURE_TEXT.fullmatch(signature) is None:
        raise SignatureError("telemetry signature encoding is invalid")
    try:
        raw = base64.b64decode(signature, validate=True)
    except ValueError:
        raise SignatureError("telemetry signature encoding is invalid") from None
    if len(raw) != SIGNATURE_LENGTH:
        raise SignatureError("telemetry signature encoding is invalid")
    return raw


def _require_envelope(event: TelemetryEnvelope | Mapping[str, object]) -> TelemetryEnvelope:
    if isinstance(event, TelemetryEnvelope):
        data: object = event.model_dump(mode="json")
    elif isinstance(event, Mapping):
        data = dict(event)
    else:
        raise TypeError("event must be a telemetry envelope")
    return TelemetryEnvelope.model_validate(data)
