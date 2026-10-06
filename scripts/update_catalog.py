#!/usr/bin/env python3
"""Rebuild the bundled operation catalog from ClickUp's official OpenAPI specs."""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SOURCES = {
    "v2": "https://developer.clickup.com/openapi/clickup-api-v2-reference.json",
    "v3": "https://developer.clickup.com/openapi/ClickUp_PUBLIC_API_V3.yaml",
}
METHODS = frozenset({"get", "put", "post", "delete", "patch", "head", "options", "trace"})
ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "src/clickup_mcp/data/operations.json"
COVERAGE_PATH = ROOT / "docs/api-coverage.md"


def read_spec(source: str | Path) -> dict[str, Any]:
    """Read JSON or YAML from a local path or one of the fixed official URLs."""
    if isinstance(source, str) and source.startswith("https://"):
        request = Request(source, headers={"User-Agent": "clickup-mcp-catalog/1.0"})
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    else:
        raw = Path(source).read_text(encoding="utf-8")
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError:
        import yaml  # Development-only dependency; runtime needs only bundled JSON.

        spec = yaml.safe_load(raw)
    if not isinstance(spec, dict) or not isinstance(spec.get("paths"), dict):
        raise ValueError(f"Invalid OpenAPI document: {source}")
    return spec


def resolve_refs(value: Any, spec: dict[str, Any], stack: tuple[str, ...] = ()) -> Any:
    """Inline local references, preserving siblings and terminating recursive schemas.

    A recursive position becomes an unconstrained schema annotated with the original
    reference, rather than an invalid reference or an infinitely expanded tree.
    External references deliberately fail so catalog updates cannot silently omit inputs.
    """
    if isinstance(value, list):
        return [resolve_refs(item, spec, stack) for item in value]
    if not isinstance(value, dict):
        return copy.deepcopy(value)
    if "$ref" not in value:
        return {key: resolve_refs(item, spec, stack) for key, item in value.items()}
    reference = value["$ref"]
    if not isinstance(reference, str) or not reference.startswith("#/"):
        raise ValueError(f"Only local OpenAPI references are supported: {reference!r}")
    siblings = {key: item for key, item in value.items() if key != "$ref"}
    if reference in stack:
        resolved = {
            "description": "Recursive schema; nested values follow the same structure.",
            "x-clickup-recursive-reference": reference,
        }
    else:
        target: Any = spec
        try:
            for part in reference[2:].split("/"):
                key = part.replace("~1", "/").replace("~0", "~")
                target = target[int(key)] if isinstance(target, list) else target[key]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ValueError(f"Unresolvable OpenAPI reference: {reference}") from exc
        resolved = resolve_refs(target, spec, (*stack, reference))
        if not isinstance(resolved, dict):
            raise ValueError(f"OpenAPI reference must resolve to an object: {reference}")
    return {**resolved, **resolve_refs(siblings, spec, stack)}


def normalize_schema(schema: Any) -> Any:
    """Add an implied object type without modifying examples or arbitrary payloads."""
    if not isinstance(schema, dict):
        return schema
    result = copy.deepcopy(schema)
    if "properties" in result and "type" not in result:
        result["type"] = "object"
    for keyword in ("properties", "$defs", "definitions", "patternProperties", "dependentSchemas"):
        if isinstance(result.get(keyword), dict):
            result[keyword] = {
                name: normalize_schema(child) for name, child in result[keyword].items()
            }
    for keyword in (
        "items",
        "additionalProperties",
        "not",
        "contains",
        "if",
        "then",
        "else",
        "propertyNames",
    ):
        if isinstance(result.get(keyword), dict):
            result[keyword] = normalize_schema(result[keyword])
        elif isinstance(result.get(keyword), list):
            result[keyword] = [normalize_schema(child) for child in result[keyword]]
    for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
        if isinstance(result.get(keyword), list):
            result[keyword] = [normalize_schema(child) for child in result[keyword]]
    return result


def full_path(
    spec: dict[str, Any], path_item: dict[str, Any], operation: dict[str, Any], path: str
) -> str:
    servers = operation.get("servers") or path_item.get("servers") or spec.get("servers")
    if not servers:
        raise ValueError(f"OpenAPI servers missing for {path}")
    server_url = servers[0]["url"]
    for name, variable in servers[0].get("variables", {}).items():
        server_url = server_url.replace("{" + name + "}", str(variable["default"]))
    server = urlsplit(server_url)
    if server.scheme != "https" or server.hostname != "api.clickup.com":
        raise ValueError(f"Unexpected ClickUp API server: {server_url}")
    result = server.path.rstrip("/") + "/" + path.lstrip("/")
    if not result.startswith(("/api/v2/", "/api/v3/")):
        raise ValueError(f"Unexpected ClickUp API path: {result}")
    return result


def build_catalog(specs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Produce deterministic, reference-free input metadata for all token-auth endpoints."""
    operations: dict[str, dict[str, Any]] = {}
    endpoints: set[tuple[str, str]] = set()
    for version, spec in sorted(specs.items()):
        for path, raw_path_item in spec["paths"].items():
            path_item = (
                resolve_refs(raw_path_item, spec) if "$ref" in raw_path_item else raw_path_item
            )
            for method, operation in path_item.items():
                if method not in METHODS:
                    continue
                original_id = operation.get("operationId")
                if original_id == "GetAccessToken":
                    continue
                if not original_id or not isinstance(original_id, str):
                    raise ValueError(f"Missing operationId for {method.upper()} {path}")
                operation_id = f"{version}_{original_id}"
                endpoint_path = full_path(spec, path_item, operation, path)
                endpoint = (method.upper(), endpoint_path)
                if operation_id in operations:
                    raise ValueError(f"Duplicate operation ID: {operation_id}")
                if endpoint in endpoints:
                    raise ValueError(f"Duplicate endpoint: {endpoint}")
                endpoints.add(endpoint)
                parameters: dict[tuple[str, str], dict[str, Any]] = {}
                for parameter in [
                    *path_item.get("parameters", []),
                    *operation.get("parameters", []),
                ]:
                    parameter = resolve_refs(parameter, spec)
                    if "schema" in parameter:
                        parameter["schema"] = normalize_schema(parameter["schema"])
                    if parameter["in"] == "query":
                        name = parameter["name"]
                        if operation_id == "v2_GetTasks" and name in {
                            "statuses",
                            "assignees",
                            "watchers",
                            "tags",
                            "custom_items",
                        }:
                            parameter["x-clickup-serialization"] = "bracket-array"
                        if (
                            operation_id in {"v2_GetTasks", "v2_GetFilteredTeamTasks", "v2_GetTask"}
                            and name == "custom_fields"
                        ):
                            parameter["x-clickup-serialization"] = "json"
                            parameter["schema"] = {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["field_id", "operator", "value"],
                                    "properties": {
                                        "field_id": {"type": "string"},
                                        "operator": {"type": "string"},
                                        "value": {},
                                    },
                                },
                            }
                    parameters[(parameter["name"], parameter["in"])] = parameter
                missing = set(re.findall(r"\{([^}]+)\}", endpoint_path)) - {
                    parameter["name"]
                    for parameter in parameters.values()
                    if parameter["in"] == "path"
                }
                if missing:
                    raise ValueError(
                        f"Missing path parameters for {operation_id}: {sorted(missing)}"
                    )
                request_body = resolve_refs(operation.get("requestBody", {}), spec)
                content = request_body.get("content", {})
                preferred = (
                    "application/json",
                    "multipart/form-data",
                    "application/x-www-form-urlencoded",
                )
                content_type = next(
                    (kind for kind in preferred if kind in content), next(iter(content), None)
                )
                body_schema = (
                    normalize_schema(content[content_type].get("schema", {}))
                    if content_type
                    else None
                )
                if operation_id == "v2_CreateTaskAttachment":
                    # Official attachment guide describes attachment[0], attachment[1], ...
                    body_schema["properties"]["attachment"]["items"] = {
                        "type": "string",
                        "format": "binary",
                    }
                doc_slug = original_id.lower().replace("'", "")
                operations[operation_id] = {
                    "operation_id": operation_id,
                    "method": method.upper(),
                    "path": endpoint_path,
                    "summary": operation.get("summary", original_id),
                    "description": operation.get("description", ""),
                    "tags": operation.get("tags", []),
                    "parameters": list(parameters.values()),
                    "body_schema": body_schema,
                    "body_required": bool(request_body.get("required", False)),
                    "content_type": content_type,
                    "deprecated": bool(operation.get("deprecated", False)),
                    "doc_url": f"https://developer.clickup.com/reference/{doc_slug}",
                }
    return dict(sorted(operations.items()))


def coverage_markdown(operations: dict[str, dict[str, Any]], snapshot_date: str) -> str:
    counts = Counter(key.split("_", 1)[0] for key in operations)
    lines = [
        "# API coverage",
        "",
        f"Official API snapshot: **{snapshot_date}**.",
        "",
        f"The bundled catalog exposes **{len(operations)} operations**: "
        f"**{counts['v2']} v2** and **{counts['v3']} v3**.",
        "",
        "Sources:",
        "",
        f"- [ClickUp API v2 OpenAPI]({SOURCES['v2']})",
        f"- [ClickUp API v3 OpenAPI]({SOURCES['v3']})",
        "",
        "The only excluded operation is `GetAccessToken` (`POST /api/v2/oauth/token`). "
        "This server uses an existing personal API token from `CLICKUP_API_KEY`; it "
        "does not perform OAuth exchanges.",
        "",
        "Coverage means every HTTP operation present in these snapshots is callable. "
        "ClickUp plan requirements, permissions, endpoint availability, and account "
        "limits still apply. "
        "Response schemas are not bundled; API responses are returned as received. "
        "Undocumented endpoints and features absent from these public "
        "specifications are not claimed as supported.",
        "",
        "## Metadata corrections and limitations",
        "",
        "- Local `$ref` inputs are expanded. Reference siblings and descriptions are retained. "
        "Recursive schema positions, if present in future specifications, are left "
        "unconstrained and marked "
        "with `x-clickup-recursive-reference` so recursion terminates without "
        "unresolved references.",
        "- An input schema declaring `properties` without `type` is normalized to `type: object`.",
        "- The v2 `CreateTaskAttachment` schema describes `attachment` as an array "
        "with empty item metadata. "
        "Items are normalized to binary strings, matching the [official attachment guide]"
        "(https://developer.clickup.com/docs/attachments). Multipart parts use "
        "`attachment[0]`, `attachment[1]`, and so on.",
        "- The v3 `postEntityAttachment` schema declares only an optional `filename`; "
        "it does not document the binary file part or its name. This catalog "
        "preserves that limitation. "
        "The multipart transport accepts explicitly named file parts; consult "
        "ClickUp for v3 file field requirements.",
        "- `GetTasks` array filters `statuses`, `assignees`, `tags`, and `custom_items` use "
        "bracketed keys despite unbracketed OpenAPI names, following "
        "[the endpoint examples](https://developer.clickup.com/reference/gettasks). "
        "The same convention is applied to `watchers`, whose reference lists an "
        "array without a wire example. "
        "These parameters carry `x-clickup-serialization: bracket-array`.",
        "- `custom_fields` for `GetTasks`, `GetFilteredTeamTasks`, and `GetTask` is corrected from "
        "an array of strings to an array of filter objects and carries "
        "`x-clickup-serialization: json`. "
        "This follows the [Custom Field filter "
        "guide](https://developer.clickup.com/docs/taskfilters) "
        "and the endpoint examples, which require a stringified JSON array containing "
        "`field_id`, `operator`, and `value`. The singular `custom_field` input "
        "retains its source schema.",
        "- Parameter names, including bracketed array names, serialization "
        "settings, required flags, and "
        "deprecation flags are retained from the source. Operation parameters "
        "override matching path-level parameters.",
        "- Reference links use lowercased operation IDs with apostrophes removed, matching the "
        "[official documentation index](https://developer.clickup.com/llms.txt) at snapshot time.",
        "",
        "## Regenerate",
        "",
        "```sh",
        "uv sync --group dev",
        "uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD",
        "```",
        "",
        "For a reproducible offline rebuild, retain both source snapshots and pass their paths:",
        "",
        "```sh",
        "uv run python scripts/update_catalog.py --v2 clickup-api-v2-reference.json \\",
        "  --v3 ClickUp_PUBLIC_API_V3.yaml --snapshot-date YYYY-MM-DD",
        "```",
        "",
        "The generator validates duplicate operation IDs, duplicate method/path pairs, "
        "unresolved references, and missing path parameters before writing either artifact.",
        "",
        "## Operations",
        "",
        "| Operation ID | Method | Path | API reference |",
        "| --- | --- | --- | --- |",
    ]
    for operation_id, operation in operations.items():
        summary = operation["summary"].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| `{operation_id}` | {operation['method']} | `{operation['path']}` | "
            f"[{summary}]({operation['doc_url']}) |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--v2", help="Local API v2 JSON/YAML snapshot (otherwise fetch official source)"
    )
    parser.add_argument(
        "--v3", help="Local API v3 JSON/YAML snapshot (otherwise fetch official source)"
    )
    parser.add_argument(
        "--snapshot-date", required=True, help="Source snapshot date in YYYY-MM-DD format"
    )
    args = parser.parse_args()
    from datetime import date

    date.fromisoformat(args.snapshot_date)
    specs = {
        version: read_spec(getattr(args, version) or source) for version, source in SOURCES.items()
    }
    operations = build_catalog(specs)
    catalog = json.dumps(operations, ensure_ascii=False, indent=2) + "\n"
    coverage = coverage_markdown(operations, args.snapshot_date)
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(catalog, encoding="utf-8")
    COVERAGE_PATH.write_text(coverage, encoding="utf-8")
    counts = Counter(key.split("_", 1)[0] for key in operations)
    print(f"Wrote {len(operations)} operations ({counts['v2']} v2, {counts['v3']} v3).")


if __name__ == "__main__":
    main()
