"""Transport tests use fake requests only; no ClickUp account is required."""

import base64
import copy
import json

import httpx
import pytest

from clickup_mcp.catalog import load_operations
from clickup_mcp.client import MAX_UPLOAD_BYTES, ClickUpClient, ClickUpError

TOKEN = "pk_test_credential_do_not_expose"


def operation(method="GET", **overrides):
    result = {
        "method": method,
        "path": "/api/v2/task/{task_id}",
        "parameters": [
            {"in": "path", "name": "task_id", "required": True, "schema": {"type": "string"}},
            {"in": "query", "name": "archived", "schema": {"type": "boolean"}},
            {
                "in": "query",
                "name": "tags[]",
                "schema": {"type": "array", "items": {"type": "string"}},
            },
        ],
        "body_schema": None,
        "body_required": False,
        "content_type": None,
    }
    result.update(overrides)
    return result


def upload_operation():
    return operation(
        "POST",
        path="/api/v2/task/{task_id}/attachment",
        content_type="multipart/form-data",
        body_required=True,
        body_schema={
            "type": "object",
            "required": ["attachment"],
            "properties": {
                "attachment": {"type": "array", "items": {"type": "string", "format": "binary"}},
                "caption": {"type": "string"},
            },
        },
    )


def upload(**overrides):
    result = {
        "field": "attachment",
        "filename": "hello.txt",
        "content_base64": base64.b64encode(b"hello").decode(),
        "content_type": "text/plain",
    }
    result.update(overrides)
    return result


@pytest.mark.parametrize(
    "token", ["", " ", " pk_x", "pk_x ", "pk_x\n", "pk_x\r", "pk_\x00", "pk_\x7f", "pk_é", None]
)
def test_invalid_tokens_do_not_appear_in_errors(token):
    with pytest.raises(ClickUpError, match="CLICKUP_API_KEY"):
        ClickUpClient(token)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True, "30"])
def test_invalid_timeouts(timeout):
    with pytest.raises(ClickUpError, match="timeout"):
        ClickUpClient(TOKEN, timeout=timeout)


async def test_raw_auth_fixed_origin_json_result_and_context_manager():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"id": "abc"})

    # Authentication does not insist on the documented pk_ prefix.
    async with ClickUpClient("legacy-token", transport=httpx.MockTransport(handler)) as client:
        result = await client.request(operation(), path_params={"task_id": "abc"})
    assert result == {"status": 200, "data": {"id": "abc"}}
    assert requests[0].headers["authorization"] == "legacy-token"
    assert str(requests[0].url) == "https://api.clickup.com/api/v2/task/abc"
    assert client._client.is_closed


async def test_proxy_environment_ignored(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://credential-thief.invalid")
    async with ClickUpClient(TOKEN) as client:
        assert client._client._trust_env is False
        assert client._client.follow_redirects is False


@pytest.mark.parametrize("status,data", [(204, None), (200, "hello")])
async def test_empty_and_non_json_responses(status, data):
    transport = httpx.MockTransport(lambda _: httpx.Response(status, text=data or ""))
    async with ClickUpClient(TOKEN, transport=transport) as client:
        assert await client.request(operation(), path_params={"task_id": "abc"}) == {
            "status": status,
            "data": data,
        }


@pytest.mark.parametrize("status", [301, 302, 307, 308])
async def test_redirects_never_forward_credentials(status):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, headers={"Location": "https://evil.invalid/stolen"})

    async with ClickUpClient(TOKEN, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ClickUpError) as exc:
            await client.request(operation(), path_params={"task_id": "abc"})
    assert exc.value.status_code == status
    assert len(requests) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500])
async def test_api_errors_redact_token_and_bound_response(status):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(status, json={"err": TOKEN + "x" * 4000})
    )
    async with ClickUpClient(TOKEN, transport=transport) as client:
        with pytest.raises(ClickUpError) as exc:
            await client.request(operation(), path_params={"task_id": "abc"})
    assert TOKEN not in str(exc.value)
    assert "[REDACTED]" in str(exc.value)
    assert exc.value.status_code == status
    assert len(str(exc.value)) < 1100


async def test_text_errors_and_success_echo_redact_secrets():
    responses = iter([httpx.Response(400, text=TOKEN), httpx.Response(200, json={TOKEN: [TOKEN]})])
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: next(responses))
    ) as client:
        with pytest.raises(ClickUpError) as exc:
            await client.request(operation(), path_params={"task_id": "abc"})
        assert TOKEN not in str(exc.value)
        result = await client.request(operation(), path_params={"task_id": "abc"})
        assert TOKEN not in json.dumps(result)


async def test_rate_limit_metadata_no_automatic_mutation_retry():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            429,
            json={"err": "rate limited"},
            headers={"Retry-After": "5", "X-RateLimit-Reset": "1800000000"},
        )

    async with ClickUpClient(TOKEN, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ClickUpError) as exc:
            await client.request(operation("DELETE"), path_params={"task_id": "abc"})
    assert exc.value.status_code == 429
    assert exc.value.retry_after == "5"
    assert exc.value.rate_limit_reset == "1800000000"
    assert "Retry explicitly" in str(exc.value)
    assert len(requests) == 1


@pytest.mark.parametrize("error_class", [httpx.ReadTimeout, httpx.ConnectError])
async def test_transport_errors_hide_secrets_and_do_not_replay(error_class):
    requests = []

    def handler(request):
        requests.append(request)
        raise error_class(TOKEN, request=request)

    async with ClickUpClient(TOKEN, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ClickUpError) as exc:
            await client.request(operation("POST"), path_params={"task_id": "abc"})
    assert TOKEN not in str(exc.value)
    assert exc.value.__suppress_context__
    assert len(requests) == 1


@pytest.mark.parametrize(
    "path",
    [
        "https://evil.invalid/",
        "//evil.invalid/api/v2/task",
        "/api/v2/../token",
        "/api/v2/./task",
        "/api/v2//task",
        "/api/v2/task?foo=x",
        "/api/v2/task#frag",
        "/api/v2/task%2Fabc",
        "/api/v2/task\\x",
        "/api/v1/task",
        "/api/v2/{invalid!}",
    ],
)
async def test_operation_paths_cannot_escape_clickup(path):
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))
    ) as client:
        with pytest.raises(ClickUpError):
            await client.request(operation(path=path), path_params={"task_id": "abc"})


@pytest.mark.parametrize(
    "identifier",
    [
        "",
        ".",
        "..",
        "a/b",
        "a\\b",
        "a?b",
        "a#b",
        "%2e%2e",
        "abc%252f",
        "abc\n",
        "abc\x00",
        True,
        None,
        [],
        1.5,
    ],
)
async def test_unsafe_path_identifiers_rejected(identifier):
    op = operation()
    op["parameters"][0]["schema"] = {}
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))
    ) as client:
        with pytest.raises(ClickUpError):
            await client.request(op, path_params={"task_id": identifier})


async def test_path_identifiers_are_url_encoded():
    requests = []
    transport = httpx.MockTransport(
        lambda request: requests.append(request) or httpx.Response(200, json={})
    )
    async with ClickUpClient(TOKEN, transport=transport) as client:
        await client.request(operation(), path_params={"task_id": "Tâche with spaces"})
    assert requests[0].url.raw_path == b"/api/v2/task/T%C3%A2che%20with%20spaces"


async def test_real_create_task_accepts_numeric_string_list_id():
    requests = []
    async with ClickUpClient(
        TOKEN,
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(201, json={"id": "abc"})
        ),
    ) as client:
        result = await client.request(
            load_operations()["v2_CreateTask"],
            path_params={"list_id": "123"},
            body={"name": "A new task"},
        )
    assert result["status"] == 201
    assert requests[0].url.path == "/api/v2/list/123/task"


async def test_real_catalog_custom_field_filters_and_array_serialization():
    requests = []
    filters = [{"field_id": "abc", "operator": ">", "value": 2}]
    async with ClickUpClient(
        TOKEN,
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(200, json={})
        ),
    ) as client:
        await client.request(
            load_operations()["v2_GetTasks"],
            path_params={"list_id": "123"},
            query={"statuses": ["to do", "in progress"], "custom_fields": filters},
        )
    assert requests[0].url.params.get_list("statuses[]") == ["to do", "in progress"]
    assert json.loads(requests[0].url.params["custom_fields"]) == filters


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"path_params": {}},
        {"path_params": {"task_id": "abc", "unknown": "x"}},
        {"path_params": {"task_id": "abc"}, "query": {"unknown": TOKEN}},
        {"path_params": {"task_id": "abc"}, "query": {"archived": "true"}},
        {"path_params": {"task_id": "abc"}, "body": {}},
        {"path_params": {"task_id": "abc"}, "files": []},
        {"path_params": []},
        {"path_params": {"task_id": "abc"}, "query": []},
    ],
)
async def test_invalid_arguments_never_reach_network(kwargs):
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))
    ) as client:
        with pytest.raises(ClickUpError) as exc:
            await client.request(operation(), **kwargs)
    assert TOKEN not in str(exc.value)


async def test_required_query_and_body_validation():
    op = operation(
        "POST",
        body_required=True,
        content_type="application/json",
        body_schema={
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "priority": {"type": "integer", "minimum": 1, "maximum": 4},
            },
        },
    )
    op["parameters"].append(
        {"in": "query", "name": "team_id", "required": True, "schema": {"type": "integer"}}
    )
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))
    ) as client:
        for kwargs in (
            {},
            {"query": {"team_id": 123}},
            {"query": {"team_id": 123}, "body": {}},
            {"query": {"team_id": 123}, "body": {"name": TOKEN, "priority": 5}},
            {"query": {"team_id": True}, "body": {"name": "Test"}},
        ):
            with pytest.raises(ClickUpError) as exc:
                await client.request(op, path_params={"task_id": "abc"}, **kwargs)
            assert TOKEN not in str(exc.value)


async def test_json_body_preserves_nested_types_and_allows_incomplete_schema_fields():
    requests = []
    body = {"name": "Task", "priority": 2, "archived": False, "custom": {"value": [1, None]}}
    op = operation(
        "POST",
        body_required=True,
        content_type="application/json",
        body_schema={"type": "object", "properties": {"name": {"type": "string"}}},
    )
    async with ClickUpClient(
        TOKEN,
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(201, json={"ok": True})
        ),
    ) as client:
        await client.request(op, path_params={"task_id": "abc"}, body=body)
    assert json.loads(requests[0].content) == body
    assert requests[0].headers["content-type"] == "application/json"


async def test_query_booleans_bracket_arrays_styles_and_json_filters():
    op = operation()
    op["parameters"].extend(
        [
            {
                "in": "query",
                "name": "statuses",
                "schema": {"type": "array"},
                "x-clickup-serialization": "bracket-array",
            },
            {
                "in": "query",
                "name": "custom_fields",
                "schema": {"type": "array", "items": {"type": "object"}},
                "x-clickup-serialization": "json",
            },
            {
                "in": "query",
                "name": "csv",
                "schema": {"type": "array"},
                "style": "form",
                "explode": False,
            },
            {
                "in": "query",
                "name": "spaces",
                "schema": {"type": "array"},
                "style": "spaceDelimited",
            },
            {"in": "query", "name": "pipes", "schema": {"type": "array"}, "style": "pipeDelimited"},
            {"in": "query", "name": "filter", "schema": {"type": "object"}, "style": "deepObject"},
        ]
    )
    filters = [{"field_id": "abc", "operator": ">", "value": 2}]
    requests = []
    async with ClickUpClient(
        TOKEN,
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(200, json={})
        ),
    ) as client:
        await client.request(
            op,
            path_params={"task_id": "abc"},
            query={
                "archived": False,
                "tags[]": ["one", "two"],
                "statuses": ["in progress", "done"],
                "custom_fields": filters,
                "csv": [1, 2],
                "spaces": [1, 2],
                "pipes": [1, 2],
                "filter": {"active": True},
            },
        )
    params = requests[0].url.params
    assert params["archived"] == "false"
    assert params.get_list("tags[]") == ["one", "two"]
    assert params.get_list("statuses[]") == ["in progress", "done"]
    assert json.loads(params["custom_fields"]) == filters
    assert params.get_list("custom_fields") == [json.dumps(filters, separators=(",", ":"))]
    assert params["csv"] == "1,2"
    assert params["spaces"] == "1 2"
    assert params["pipes"] == "1|2"
    assert params["filter[active]"] == "true"


async def test_nullable_openapi_schema_is_supported():
    op = operation(
        "PATCH",
        content_type="application/json",
        body_schema={
            "type": "object",
            "properties": {"priority": {"type": "integer", "nullable": True}},
        },
    )
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: httpx.Response(200, json={}))
    ) as client:
        await client.request(op, path_params={"task_id": "abc"}, body={"priority": None})


async def test_multipart_uploads_have_boundary_and_indexed_parts():
    requests = []
    original = upload_operation()
    expected = copy.deepcopy(original)
    async with ClickUpClient(
        TOKEN,
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(200, json={})
        ),
    ) as client:
        await client.request(
            original,
            path_params={"task_id": "abc"},
            body={"caption": "Hi"},
            files=[upload(), upload(filename="second.txt")],
        )
    request = requests[0]
    assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
    assert b'name="attachment[0]"; filename="hello.txt"' in request.content
    assert b'name="attachment[1]"; filename="second.txt"' in request.content
    assert b'name="caption"' in request.content
    assert b"hello" in request.content
    assert original == expected


async def test_v3_omitted_binary_schema_accepts_explicit_safe_field():
    op = operation(
        "POST",
        path="/api/v3/workspaces/{task_id}/attachments/abc/attachments",
        content_type="multipart/form-data",
        body_schema={
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "additionalProperties": False,
        },
    )
    requests = []
    async with ClickUpClient(
        TOKEN,
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(200, json={})
        ),
    ) as client:
        await client.request(
            op,
            path_params={"task_id": "123"},
            body={"filename": "override.txt"},
            files=[upload(field="attachment")],
        )
    assert b'name="attachment"; filename="hello.txt"' in requests[0].content


@pytest.mark.parametrize(
    "file",
    [
        upload(field="unknown"),
        upload(field="caption"),
        upload(field="attachment\r\nBad"),
        upload(filename="../secret"),
        upload(filename="x\x00.txt"),
        upload(content_type="text/plain\r\nBad"),
        upload(content_base64="not base64"),
        upload(content_base64="aGVsbG8=\n"),
        {"path": "/etc/passwd"},
        {"url": "https://evil.invalid"},
    ],
)
async def test_invalid_uploads_rejected_without_file_or_network_access(file):
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))
    ) as client:
        with pytest.raises(ClickUpError):
            await client.request(upload_operation(), path_params={"task_id": "abc"}, files=[file])


async def test_upload_total_limit_is_bounded(monkeypatch):
    monkeypatch.setattr("clickup_mcp.client.MAX_UPLOAD_BYTES", 8)
    assert MAX_UPLOAD_BYTES == 10 * 1024 * 1024
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))
    ) as client:
        for files in (
            [upload(), upload()],
            [upload(content_base64=base64.b64encode(b"a" * 10).decode())],
        ):
            with pytest.raises(ClickUpError, match="10 MiB"):
                await client.request(
                    upload_operation(), path_params={"task_id": "abc"}, files=files
                )


async def test_missing_upload_required_and_binary_in_body_rejected():
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))
    ) as client:
        for kwargs in (
            {},
            {"files": []},
            {"body": {"caption": "Hi"}},
            {"body": {"attachment": ["fake"]}},
            {"body": {"attachment": ["fake"]}, "files": [upload()]},
            {"files": {}},
        ):
            with pytest.raises(ClickUpError):
                await client.request(upload_operation(), path_params={"task_id": "abc"}, **kwargs)


async def test_form_body_uses_lowercase_boolean_and_json_objects():
    op = operation(
        "POST", content_type="application/x-www-form-urlencoded", body_schema={"type": "object"}
    )
    requests = []
    async with ClickUpClient(
        TOKEN,
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(200, json={})
        ),
    ) as client:
        await client.request(
            op, path_params={"task_id": "abc"}, body={"enabled": False, "values": [1, 2]}
        )
    assert requests[0].content == b"enabled=false&values=%5B1%2C2%5D"


@pytest.mark.parametrize(
    "operation_id", ["v3_replaceTimeEstimatesByUser", "v3_updateTimeEstimatesByUser"]
)
@pytest.mark.parametrize("body", [[], [{"assignee": "unassigned", "time": 0}]])
async def test_time_estimates_send_top_level_arrays(operation_id, body):
    requests = []
    async with ClickUpClient(
        TOKEN,
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(200, json={})
        ),
    ) as client:
        await client.request(
            load_operations()[operation_id],
            path_params={"workspace_id": "123", "task_id": "abc"},
            body=body,
        )
    assert json.loads(requests[0].content) == body
    assert requests[0].headers["content-type"] == "application/json"


@pytest.mark.parametrize("body", [{}, [{"assignee": "unassigned", "time": -1}], [{"time": 1}]])
async def test_time_estimates_reject_wrong_shape_and_invalid_items(body):
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))
    ) as client:
        with pytest.raises(ClickUpError):
            await client.request(
                load_operations()["v3_replaceTimeEstimatesByUser"],
                path_params={"workspace_id": "123", "task_id": "abc"},
                body=body,
            )


@pytest.mark.parametrize("operation_id", ["v2_GetSpaceTags", "v2_DeleteTask"])
async def test_bodyless_operations_send_documented_fixed_content_type(operation_id):
    op = load_operations()[operation_id]
    requests = []
    async with ClickUpClient(
        TOKEN,
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(200, json={})
        ),
    ) as client:
        await client.request(
            op,
            path_params={
                parameter["name"]: "123"
                for parameter in op["parameters"]
                if parameter["in"] == "path"
            },
        )
    assert requests[0].headers["content-type"] == "application/json"
    assert requests[0].content == b""


@pytest.mark.parametrize(
    "content_type", ["multipart/form-data", "application/x-www-form-urlencoded"]
)
async def test_non_json_transports_reject_array_metadata(content_type):
    op = operation("POST", content_type=content_type, body_schema={"type": "array"})
    async with ClickUpClient(
        TOKEN, transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))
    ) as client:
        with pytest.raises(ClickUpError, match="object"):
            await client.request(op, path_params={"task_id": "abc"}, body=[])
