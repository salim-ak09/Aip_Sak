from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, ValidationError

from venice_pt.contracts.tools import ToolSpec


class ManifestSchemaError(Exception):
    pass


class StrictToolManifest(ToolSpec):
    # Strict validation: forbid any unknown extra fields in the YAML manifest
    model_config = ConfigDict(extra="forbid")


def validate_manifest_dict(raw: dict[str, Any]) -> StrictToolManifest:
    try:
        return StrictToolManifest.model_validate(raw)
    except ValidationError as e:
        raise ManifestSchemaError(f"Invalid tool manifest: {e}") from e
