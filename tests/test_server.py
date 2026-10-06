"""Exercise MCP discovery, execution, and CLI behavior through the real SDK."""

from __future__ import annotations

import os
import subprocess
import sys

import httpx
import pytest
from mcp import Client, StdioServerParameters

from clickup_mcp.server import create_server


@pytest.fixture
def requests():
    return []


@pytest.fixture
def transport(requests):
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={"teams": [{"id": "123", "name": "Example"}]})

    return httpx.MockTransport(handle)


async def test_mcp_discovery_and_read(transport, requests):
    async with Client(create_server("pk_test", transport=transport)) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        assert set(tools) == {
            "clickup_search_operations",
            "clickup_get_operation",
            "clickup_read",
            "clickup_write",
        }
        assert tools["clickup_read"].annotations.read_only_hint is True
        assert tools["clickup_write"].annotations.destructive_hint is True
        assert tools["clickup_write"].annotations.idempotent_hint is False
        found = await client.call_tool(
            "clickup_search_operations", {"search": "authorized workspaces"}
        )
        assert not found.is_error
        assert "v2_GetAuthorizedTeams" in {
            op["operation_id"] for op in found.structured_content["operations"]
        }
        schema = await client.call_tool("clickup_get_operation", {"operation_id": "v2_CreateTask"})
        assert schema.structured_content["body_schema"]["required"] == ["name"]
        assert not requests  # Discovery stays offline.
        result = await client.call_tool("clickup_read", {"operation_id": "v2_GetAuthorizedTeams"})
        assert result.structured_content == {
            "status": 200,
            "data": {"teams": [{"id": "123", "name": "Example"}]},
        }
        assert requests[0].url == "https://api.clickup.com/api/v2/team"
        assert requests[0].headers["Authorization"] == "pk_test"


async def test_read_only_cannot_discover_or_execute_writes(transport, requests):
    async with Client(create_server("pk_test", read_only=True, transport=transport)) as client:
        assert "clickup_write" not in {tool.name for tool in (await client.list_tools()).tools}
        found = await client.call_tool("clickup_search_operations", {"limit": 100})
        assert all(op["method"] == "GET" for op in found.structured_content["operations"])
        for tool in ("clickup_read", "clickup_get_operation"):
            result = await client.call_tool(tool, {"operation_id": "v2_DeleteTask"})
            assert result.is_error
        result = await client.call_tool("clickup_write", {"operation_id": "v2_DeleteTask"})
        assert result.is_error
        assert not requests


async def test_write_and_wrong_tool_rejection(transport, requests):
    async with Client(create_server("pk_test", transport=transport)) as client:
        result = await client.call_tool(
            "clickup_write",
            {
                "operation_id": "v2_CreateTask",
                "path_params": {"list_id": "123"},
                "body": {"name": "Example"},
            },
        )
        assert not result.is_error
        assert requests[0].method == "POST"
        assert requests[0].content == b'{"name":"Example"}'
        for tool, operation in (
            ("clickup_write", "v2_GetAuthorizedTeams"),
            ("clickup_read", "v2_CreateTask"),
        ):
            result = await client.call_tool(tool, {"operation_id": operation})
            assert result.is_error
        assert len(requests) == 1


async def test_catalog_pagination_and_input_validation(transport, requests):
    async with Client(create_server("pk_test", transport=transport)) as client:
        first = (
            await client.call_tool("clickup_search_operations", {"limit": 1})
        ).structured_content
        second = (
            await client.call_tool(
                "clickup_search_operations", {"limit": 1, "offset": first["next_offset"]}
            )
        ).structured_content
        assert first["total"] == 172
        assert first["operations"] != second["operations"]
        for args in ({"limit": 101}, {"offset": -1}, {"version": "v4"}):
            assert (await client.call_tool("clickup_search_operations", args)).is_error
        assert (
            await client.call_tool("clickup_get_operation", {"operation_id": "https://example.org"})
        ).is_error
        assert not requests


async def test_http_error_is_a_safe_mcp_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"err": "pk_secret denied"})
    )
    async with Client(create_server("pk_secret", transport=transport)) as client:
        result = await client.call_tool("clickup_read", {"operation_id": "v2_GetAuthorizedTeams"})
        assert result.is_error
        assert "pk_secret" not in str(result)
        assert "401" in str(result)


@pytest.mark.parametrize(
    "operation_id", ["v3_replaceTimeEstimatesByUser", "v3_updateTimeEstimatesByUser"]
)
async def test_mcp_write_accepts_documented_array_bodies(operation_id, transport, requests):
    async with Client(create_server("pk_test", transport=transport)) as client:
        result = await client.call_tool(
            "clickup_write",
            {
                "operation_id": operation_id,
                "path_params": {"workspace_id": "123", "task_id": "abc"},
                "body": [{"assignee": "unassigned", "time": 0}],
            },
        )
        assert not result.is_error
        assert requests[0].content == b'[{"assignee":"unassigned","time":0}]'


async def test_actual_stdio_handshake():
    # A fake token suffices: initializing and browsing the catalog never calls ClickUp.
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "clickup_mcp", "--read-only"],
        env={**os.environ, "CLICKUP_API_KEY": "pk_stdio_test"},
    )
    async with Client(params) as client:
        assert len((await client.list_tools()).tools) == 3
        result = await client.call_tool(
            "clickup_get_operation", {"operation_id": "v2_GetAuthorizedTeams"}
        )
        assert not result.is_error
        assert result.structured_content["path"] == "/api/v2/team"


@pytest.mark.parametrize("args", [["--help"], ["--version"]])
def test_cli_metadata_without_token(args):
    result = subprocess.run(
        [sys.executable, "-m", "clickup_mcp", *args],
        env={**os.environ, "CLICKUP_API_KEY": ""},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout


def test_missing_token_fails_cleanly():
    result = subprocess.run(
        [sys.executable, "-m", "clickup_mcp"],
        env={**os.environ, "CLICKUP_API_KEY": ""},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "CLICKUP_API_KEY" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "invalid"])
def test_invalid_timeout_fails(value):
    result = subprocess.run(
        [sys.executable, "-m", "clickup_mcp", "--timeout", value],
        env={**os.environ, "CLICKUP_API_KEY": "pk_test"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert result.stdout == ""
