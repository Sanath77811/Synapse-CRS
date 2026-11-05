"""Target scope rules for v0.1.

A scope names an owned lab or development asset. It is not a permission to
contact that asset. The API never opens a connection from a scope value.
"""

import re
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from synapse_contracts.text import BoundedDescription, reject_unbounded_text

ASSET_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
FORBIDDEN_ASSETS = frozenset({"*", "0.0.0.0", "::", "0.0.0.0/0"})


class EnvironmentKind(StrEnum):
    LAB = "lab"
    DEVELOPMENT = "development"


class TargetScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment: EnvironmentKind
    assets: Annotated[list[str], Field(min_length=1, max_length=32)]
    description: BoundedDescription

    @field_validator("description")
    @classmethod
    def description_text(cls, value: str) -> str:
        return reject_unbounded_text(value)

    @field_validator("assets")
    @classmethod
    def bounded_assets(cls, assets: list[str]) -> list[str]:
        for asset in assets:
            if asset in FORBIDDEN_ASSETS or ASSET_PATTERN.fullmatch(asset) is None:
                raise ValueError(
                    "assets must be bounded identifiers using letters, digits, "
                    "'.', '_', ':', or '-'"
                )
        if len(set(assets)) != len(assets):
            raise ValueError("assets must be unique")
        return assets
