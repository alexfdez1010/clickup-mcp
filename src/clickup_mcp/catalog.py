"""Load the packaged, offline ClickUp API input catalog."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def load_operations() -> dict[str, dict[str, Any]]:
    """Return a fresh operation mapping, without network access or API credentials."""
    resource = files("clickup_mcp").joinpath("data", "operations.json")
    return json.loads(resource.read_text(encoding="utf-8"))
