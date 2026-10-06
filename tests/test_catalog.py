"""Regression checks for the packaged official API catalog and its generator."""

from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from clickup_mcp.catalog import load_operations

GENERATOR_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_catalog.py"
SPEC = importlib.util.spec_from_file_location("update_catalog", GENERATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def minimal_spec(paths: dict[str, Any], components: dict[str, Any] | None = None):
    return {
        "servers": [{"url": "https://api.clickup.com/api"}],
        "paths": paths,
        "components": components or {},
    }


def test_snapshot_covers_all_documented_token_operations():
    operations = load_operations()
    assert len(operations) == 172
    assert Counter(key.split("_", 1)[0] for key in operations) == {"v2": 137, "v3": 35}
    assert "v2_GetAccessToken" not in operations
    assert "v2_GetAuthorizedUser" in operations
    assert "v2_CreateTask" in operations
    assert "v3_createChatMessage" in operations
    assert "v3_createDocPublic" in operations
    assert "v3_postEntityAttachment" in operations
    assert (
        len({(operation["method"], operation["path"]) for operation in operations.values()}) == 172
    )
    for operation_id, operation in operations.items():
        assert operation["operation_id"] == operation_id
        assert operation["path"].startswith(("/api/v2/", "/api/v3/"))
        assert all("$ref" not in item for item in walk(operation))
        assert set(operation) == {
            "operation_id",
            "method",
            "path",
            "summary",
            "description",
            "tags",
            "parameters",
            "body_schema",
            "body_required",
            "content_type",
            "deprecated",
            "doc_url",
        }


def test_offline_load_returns_independent_mutable_mappings():
    first = load_operations()
    first["v2_CreateTask"]["body_schema"]["properties"].clear()
    assert load_operations()["v2_CreateTask"]["body_schema"]["properties"]


def test_multipart_metadata_preserves_documented_gap():
    operations = load_operations()
    task = operations["v2_CreateTaskAttachment"]
    assert task["content_type"] == "multipart/form-data"
    assert task["body_required"] is True
    assert task["body_schema"]["type"] == "object"
    assert task["body_schema"]["properties"]["attachment"] == {
        "type": "array",
        "items": {"type": "string", "format": "binary"},
    }
    entity = operations["v3_postEntityAttachment"]
    assert entity["content_type"] == "multipart/form-data"
    assert set(entity["body_schema"]["properties"]) == {"filename"}


def test_parameter_override_and_reference_expansion():
    spec = minimal_spec(
        {
            "/v2/task/{task_id}": {
                "parameters": [
                    {
                        "name": "task_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {
                    "operationId": "Example",
                    "deprecated": True,
                    "parameters": [
                        {
                            "name": "task_id",
                            "in": "path",
                            "required": True,
                            "description": "Override",
                            "schema": {"type": "integer"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Body",
                                    "description": "Local description",
                                }
                            },
                            "multipart/form-data": {"schema": {"type": "string"}},
                        },
                    },
                },
            }
        },
        {
            "schemas": {
                "Body": {"properties": {"name": {"type": "string"}}, "description": "Original"}
            }
        },
    )
    operation = GENERATOR.build_catalog({"v2": spec})["v2_Example"]
    assert len(operation["parameters"]) == 1
    assert operation["parameters"][0]["description"] == "Override"
    assert operation["parameters"][0]["schema"] == {"type": "integer"}
    assert operation["body_schema"] == {
        "type": "object",
        "description": "Local description",
        "properties": {"name": {"type": "string"}},
    }
    assert operation["content_type"] == "application/json"
    assert operation["deprecated"] is True


def test_recursive_refs_terminate_and_preserve_siblings():
    spec = {
        "components": {
            "schemas": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "next": {"$ref": "#/components/schemas/Node", "description": "Next node"},
                    },
                }
            }
        }
    }
    expanded = GENERATOR.resolve_refs({"$ref": "#/components/schemas/Node"}, spec)
    assert expanded["properties"]["next"]["description"] == "Next node"
    assert (
        expanded["properties"]["next"]["x-clickup-recursive-reference"]
        == "#/components/schemas/Node"
    )
    assert all("$ref" not in item for item in walk(expanded))


def test_pointer_escaping_and_normalization_do_not_modify_examples():
    spec = {"components": {"schemas": {"a/b~c": {"type": "string"}}}}
    assert GENERATOR.resolve_refs({"$ref": "#/components/schemas/a~1b~0c"}, spec) == {
        "type": "string"
    }
    schema = {
        "properties": {"nested": {"properties": {"field": {"type": "integer"}}}},
        "example": {"properties": {"x": "data"}},
    }
    normalized = GENERATOR.normalize_schema(schema)
    assert normalized["type"] == "object"
    assert normalized["properties"]["nested"]["type"] == "object"
    assert normalized["example"] == schema["example"]
    assert "type" not in schema


@pytest.mark.parametrize(
    "reference", ["https://example.com/schema.json", "#/components/schemas/Missing"]
)
def test_invalid_refs_fail_explicitly(reference):
    with pytest.raises(ValueError):
        GENERATOR.resolve_refs({"$ref": reference}, {})


def test_duplicate_ids_and_missing_path_parameters_fail():
    with pytest.raises(ValueError, match="Duplicate operation ID"):
        GENERATOR.build_catalog(
            {
                "v2": minimal_spec(
                    {
                        "/v2/first": {"get": {"operationId": "Duplicate"}},
                        "/v2/second": {"get": {"operationId": "Duplicate"}},
                    }
                )
            }
        )
    with pytest.raises(ValueError, match="Missing path parameters"):
        GENERATOR.build_catalog(
            {"v2": minimal_spec({"/v2/task/{task_id}": {"get": {"operationId": "Missing"}}})}
        )


def test_local_json_and_yaml_sources(tmp_path):
    document = minimal_spec({"/v2/user": {"get": {"operationId": "User"}}})
    json_path = tmp_path / "api.json"
    json_path.write_text(json.dumps(document), encoding="utf-8")
    assert GENERATOR.read_spec(json_path) == document
    yaml_path = tmp_path / "api.yaml"
    yaml_path.write_text(
        "servers:\n  - url: https://api.clickup.com/api\npaths: {}\n", encoding="utf-8"
    )
    assert GENERATOR.read_spec(yaml_path)["paths"] == {}


def test_catalog_generation_is_deterministic():
    document = minimal_spec(
        {
            "/v2/z": {"get": {"operationId": "Z"}},
            "/v2/a": {"get": {"operationId": "A"}},
        }
    )
    catalog = GENERATOR.build_catalog({"v2": document})
    assert list(catalog) == ["v2_A", "v2_Z"]
    reversed_document = {**document, "paths": dict(reversed(list(document["paths"].items())))}
    rebuilt = GENERATOR.build_catalog({"v2": reversed_document})
    assert json.dumps(rebuilt) == json.dumps(catalog)
    coverage = GENERATOR.coverage_markdown(catalog, "2026-10-06")
    assert coverage.index("`v2_A`") < coverage.index("`v2_Z`")


def test_documented_task_filter_serialization_overrides():
    operations = load_operations()
    for operation_id in ("v2_GetTask", "v2_GetTasks", "v2_GetFilteredTeamTasks"):
        parameter = next(
            parameter
            for parameter in operations[operation_id]["parameters"]
            if parameter["name"] == "custom_fields"
        )
        assert parameter["x-clickup-serialization"] == "json"
        assert parameter["schema"]["items"]["required"] == ["field_id", "operator", "value"]
        assert parameter["schema"]["items"]["properties"]["value"] == {}
    parameters = {p["name"]: p for p in operations["v2_GetTasks"]["parameters"]}
    for name in ("statuses", "assignees", "watchers", "tags", "custom_items"):
        assert parameters[name]["x-clickup-serialization"] == "bracket-array"
    assert "x-clickup-serialization" not in parameters["custom_field"]


def test_time_in_status_documentation_slugs_remove_apostrophes():
    operations = load_operations()
    assert operations["v2_GetTask'sTimeinStatus"]["doc_url"].endswith("/gettaskstimeinstatus")
    assert operations["v2_GetBulkTasks'TimeinStatus"]["doc_url"].endswith(
        "/getbulktaskstimeinstatus"
    )
