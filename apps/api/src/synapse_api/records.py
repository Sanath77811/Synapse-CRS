"""Map stored targets into policy records. Invalid scope fails closed."""

from pydantic import ValidationError
from synapse_contracts.scope import TargetScope
from synapse_policy import TargetRecord

from synapse_api.models import TargetRow


def target_record(row: TargetRow) -> TargetRecord:
    scope = None
    scope_reasons: tuple[str, ...] = ()
    try:
        scope = TargetScope.model_validate(row.scope)
    except ValidationError:
        scope_reasons = ("scope_invalid",)
    capabilities = row.allowed_capabilities
    if not isinstance(capabilities, list):
        capabilities = []
    return TargetRecord(
        target_id=row.id,
        owner=row.owner,
        stored_status=row.authorization_status,
        authorization_expiry=row.authorization_expiry,
        capabilities=tuple(str(item) for item in capabilities),
        scope=scope,
        scope_reasons=scope_reasons,
    )
