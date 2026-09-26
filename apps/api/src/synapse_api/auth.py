"""Bearer-token authentication and role checks."""

import hashlib
import hmac
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from synapse_api.config import Principal, get_settings
from synapse_api.errors import ApiError

_bearer = HTTPBearer(auto_error=False)


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def authenticate(token: str) -> Principal | None:
    principals = get_settings().principals()
    for candidate, principal in principals.items():
        if hmac.compare_digest(_digest(token), _digest(candidate)):
            return principal
    return None


def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "authentication_required", "A bearer token is required.")
    principal = authenticate(credentials.credentials)
    if principal is None:
        raise ApiError(401, "authentication_failed", "The bearer token was rejected.")
    return principal


def require_admin(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
    if principal.role != "admin":
        raise ApiError(403, "authorization_failed", "This action requires the admin role.")
    return principal
