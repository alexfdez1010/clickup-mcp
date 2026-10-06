"""Validated, credential-safe transport for the published ClickUp API."""

from __future__ import annotations

import base64
import binascii
import json
import math
import re
from typing import Any
from urllib.parse import quote

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_ORIGIN = "https://api.clickup.com"
_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_FIELD = re.compile(r"[A-Za-z0-9_.-]+(?:\[(?:[0-9]*)\])?\Z")
_MIME = re.compile(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+\Z")


class ClickUpError(ValueError):
    """A safe error with optional HTTP and rate-limit metadata."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: str | None = None,
        rate_limit_reset: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after
        self.rate_limit_reset = rate_limit_reset


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), allow_nan=False)
    return str(value)


def _schema_for_validation(schema: Any) -> Any:
    """Support OpenAPI 3.0 nullable alongside JSON Schema's native types."""
    if isinstance(schema, list):
        return [_schema_for_validation(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    result = {key: _schema_for_validation(value) for key, value in schema.items()}
    if result.get("nullable") is True:
        result.pop("nullable")
        return {"anyOf": [result, {"type": "null"}]}
    return result


class ClickUpClient:
    """Send requests only to ClickUp, using a raw personal-token header."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 30,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if (
            not isinstance(api_key, str)
            or not api_key
            or api_key != api_key.strip()
            or any(ord(char) < 33 or ord(char) > 126 for char in api_key)
        ):
            raise ClickUpError("CLICKUP_API_KEY must be a nonempty ASCII token without whitespace.")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ClickUpError("Request timeout must be a positive finite number.")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            headers={"Authorization": api_key, "Accept": "application/json"},
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
            trust_env=False,
        )

    async def __aenter__(self) -> ClickUpClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _redact(self, value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(self._api_key, "[REDACTED]")
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, dict):
            return {self._redact(key): self._redact(item) for key, item in value.items()}
        return value

    def _validate(self, value: Any, schema: dict[str, Any] | None, label: str) -> None:
        if not schema:
            return
        try:
            validator = Draft202012Validator(_schema_for_validation(schema))
            error = next(validator.iter_errors(value), None)
        except (SchemaError, ValueError, TypeError, RecursionError):
            raise ClickUpError(f"Cannot validate the documented schema for {label}.") from None
        if error is not None:
            location = ".".join(str(part) for part in error.absolute_path)
            suffix = f" at {location}" if location else ""
            # jsonschema messages include supplied values; report constraints only.
            raise ClickUpError(
                self._redact(f"Invalid {label}{suffix}: failed {error.validator} validation.")
            )

    @staticmethod
    def _parameters(values: dict[str, Any] | None, label: str) -> dict[str, Any]:
        if values is None:
            return {}
        if not isinstance(values, dict) or any(not isinstance(key, str) for key in values):
            raise ClickUpError(f"{label} must be an object with string keys.")
        return values

    def _url_and_query(
        self,
        operation: dict[str, Any],
        path_params: dict[str, Any],
        query: dict[str, Any],
    ) -> tuple[str, list[tuple[str, str]]]:
        method, path = operation.get("method"), operation.get("path")
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ClickUpError("Unsupported API method.")
        if not isinstance(path, str) or not re.fullmatch(r"/api/v[23]/[A-Za-z0-9_{}./-]+", path):
            raise ClickUpError("Invalid ClickUp API path.")
        if any(part in {".", "..", ""} for part in path.split("/")[1:]):
            raise ClickUpError("Invalid ClickUp API path.")
        names = set(_PLACEHOLDER.findall(path))
        if "{" in _PLACEHOLDER.sub("", path) or "}" in _PLACEHOLDER.sub("", path):
            raise ClickUpError("Invalid API path placeholder.")
        parameters = operation.get("parameters", [])
        declared = {location: {} for location in ("path", "query")}
        for parameter in parameters:
            location = parameter.get("in")
            if location in declared:
                declared[location][parameter["name"]] = parameter
        if set(path_params) - names or names - set(path_params):
            raise ClickUpError("Path parameters must exactly match the documented API path.")
        if set(query) - set(declared["query"]):
            raise ClickUpError(
                "Unknown query parameter; use the operation's documented parameters."
            )
        for location, supplied in (("path", path_params), ("query", query)):
            for name, parameter in declared[location].items():
                if parameter.get("required") and name not in supplied:
                    raise ClickUpError(
                        self._redact(f"Missing required {location} parameter: {name}.")
                    )
                if name in supplied:
                    value = supplied[name]
                    schema = parameter.get("schema", {})
                    # ClickUp responses return many numeric IDs as strings.
                    # Validate digit-only path IDs numerically without changing the wire ID.
                    if (
                        location == "path"
                        and schema.get("type") in ("integer", "number")
                        and isinstance(value, str)
                        and re.fullmatch(r"[0-9]+", value)
                    ):
                        value = int(value)
                    self._validate(value, schema, f"{location} parameter {name}")
        for name in names:
            value = path_params[name]
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise ClickUpError("Path identifiers must be strings or integers.")
            value = str(value)
            if (
                not value
                or value in {".", ".."}
                or any(char in value for char in "/\\%?#")
                or _CONTROL.search(value)
            ):
                raise ClickUpError("Path identifier contains unsafe URL characters.")
            path = path.replace("{" + name + "}", quote(value, safe=""))
        pairs: list[tuple[str, str]] = []
        for name, value in query.items():
            parameter = declared["query"][name]
            style = parameter.get("style", "form")
            explode = parameter.get("explode", style == "form")
            serialization = parameter.get("x-clickup-serialization")
            if serialization == "json":
                pairs.append((name, _scalar(value)))
                continue
            if serialization == "bracket-array" and isinstance(value, list):
                wire_name = name if name.endswith("[]") else name + "[]"
                pairs.extend((wire_name, _scalar(item)) for item in value)
                continue
            if isinstance(value, list):
                if style == "form" and explode:
                    pairs.extend((name, _scalar(item)) for item in value)
                elif style in {"form", "spaceDelimited", "pipeDelimited"}:
                    delimiter = {"form": ",", "spaceDelimited": " ", "pipeDelimited": "|"}[style]
                    pairs.append((name, delimiter.join(_scalar(item) for item in value)))
                else:
                    raise ClickUpError("Unsupported query array serialization style.")
            elif isinstance(value, dict):
                if style == "deepObject":
                    pairs.extend((f"{name}[{key}]", _scalar(item)) for key, item in value.items())
                else:
                    # ClickUp's custom_fields filters are JSON in the query string.
                    pairs.append((name, _scalar(value)))
            else:
                pairs.append((name, _scalar(value)))
        return _ORIGIN + path, pairs

    def _uploads(
        self,
        files: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        *,
        allow_undocumented_fields: bool = False,
    ) -> tuple[list[tuple[str, tuple[str, bytes, str]]], dict[str, Any]]:
        if not isinstance(files, list):
            raise ClickUpError("Files must be a list of upload objects.")
        result = []
        synthetic: dict[str, Any] = {}
        total = 0
        properties = (schema or {}).get("properties", {})
        for file in files:
            if not isinstance(file, dict) or set(file) != {
                "field",
                "filename",
                "content_base64",
                "content_type",
            }:
                raise ClickUpError(
                    "Each file needs field, filename, content_base64, and content_type."
                )
            field, filename, encoded, content_type = (
                file[key] for key in ("field", "filename", "content_base64", "content_type")
            )
            if not isinstance(field, str) or len(field) > 128 or not _FIELD.fullmatch(field):
                raise ClickUpError("Invalid multipart field name.")
            base_field = field.split("[", 1)[0]
            if base_field not in properties:
                if not allow_undocumented_fields:
                    raise ClickUpError(
                        "Upload field is absent from the documented multipart schema."
                    )
            field_schema = properties.get(base_field, {"type": "string", "format": "binary"})
            is_array = field_schema.get("type") == "array"
            binary_schema = field_schema.get("items", {}) if is_array else field_schema
            if binary_schema.get("format") != "binary":
                raise ClickUpError("Upload field must be a documented binary property.")
            if "[" in field and not is_array:
                raise ClickUpError("Indexed file fields require an array upload property.")
            if (
                not isinstance(filename, str)
                or not filename
                or len(filename) > 255
                or _CONTROL.search(filename)
                or any(char in filename for char in "/\\")
            ):
                raise ClickUpError(
                    "Upload filename must be a plain filename without path or control characters."
                )
            if not isinstance(content_type, str) or not _MIME.fullmatch(content_type):
                raise ClickUpError("Upload content_type must be a valid MIME type.")
            if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_UPLOAD_BYTES + 2) // 3):
                raise ClickUpError("Total decoded uploads must not exceed 10 MiB.")
            try:
                decoded = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error):
                raise ClickUpError("Upload content_base64 must contain valid base64.") from None
            total += len(decoded)
            if total > MAX_UPLOAD_BYTES:
                raise ClickUpError("Total decoded uploads must not exceed 10 MiB.")
            if is_array:
                synthetic.setdefault(base_field, []).append(filename)
            elif base_field in synthetic:
                raise ClickUpError("A single-file upload property cannot be repeated.")
            else:
                synthetic[base_field] = filename
            # ClickUp documents attachment[0]/attachment[1] for v2 arrays.
            wire_field = (
                f"{base_field}[{len(synthetic[base_field]) - 1}]"
                if is_array and field == base_field
                else field
            )
            result.append((wire_field, (filename, decoded, content_type)))
        if allow_undocumented_fields:
            synthetic = {key: value for key, value in synthetic.items() if key in properties}
        return result, synthetic

    async def request(
        self,
        operation: dict[str, Any],
        *,
        path_params: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | list[Any] | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Validate and send one request; mutations are never automatically retried."""
        if not isinstance(operation, dict):
            raise ClickUpError("Operation must be a documented API operation object.")
        url, params = self._url_and_query(
            operation,
            self._parameters(path_params, "Path parameters"),
            self._parameters(query, "Query parameters"),
        )
        if body is not None and not isinstance(body, (dict, list)):
            raise ClickUpError("Request body must be an object or array.")
        schema, content_type = operation.get("body_schema"), operation.get("content_type")
        if body is not None and schema is None:
            raise ClickUpError("This operation does not accept a request body.")
        if files is not None and content_type != "multipart/form-data":
            raise ClickUpError("Files are only accepted by multipart upload operations.")
        kwargs: dict[str, Any] = {"params": params}
        # Some bodyless GET/DELETE operations explicitly require this fixed header.
        # Only accept the trusted media type, never caller-supplied header values.
        if content_type is None and any(
            parameter.get("in") == "header"
            and parameter.get("name", "").lower() == "content-type"
            and parameter.get("schema", {}).get("const") == "application/json"
            for parameter in operation.get("parameters", [])
        ):
            kwargs["headers"] = {"Content-Type": "application/json"}
        if content_type == "multipart/form-data":
            if body is not None and not isinstance(body, dict):
                raise ClickUpError("Multipart request metadata must be an object.")
            uploads, synthetic = self._uploads(
                files if files is not None else [],
                schema,
                # The published v3 attachment schema omits the binary field.
                allow_undocumented_fields=operation["path"].startswith("/api/v3/"),
            )
            values = dict(body or {})
            binary_fields = {
                name
                for name, field_schema in (schema or {}).get("properties", {}).items()
                if field_schema.get("format") == "binary"
                or field_schema.get("items", {}).get("format") == "binary"
            }
            if set(values) & (set(synthetic) | binary_fields):
                raise ClickUpError("Provide binary fields through files only.")
            values.update(synthetic)
            if operation.get("body_required") and not values and not uploads:
                raise ClickUpError("This operation requires a request body or upload.")
            self._validate(values, schema, "request body")
            if uploads:
                # Encode metadata as multipart text parts alongside uploaded files.
                kwargs["files"] = [
                    (name, (None, _scalar(value))) for name, value in (body or {}).items()
                ] + uploads
            elif body:
                kwargs["files"] = [(name, (None, _scalar(value))) for name, value in body.items()]
        else:
            if operation.get("body_required") and body is None:
                raise ClickUpError("This operation requires a request body.")
            if body is not None:
                self._validate(body, schema, "request body")
                if content_type in (None, "application/json"):
                    kwargs["json"] = body
                elif content_type == "application/x-www-form-urlencoded":
                    if not isinstance(body, dict):
                        raise ClickUpError("Form request body must be an object.")
                    kwargs["data"] = {name: _scalar(value) for name, value in body.items()}
                else:
                    raise ClickUpError("Unsupported documented request content type.")
        try:
            response = await self._client.request(operation["method"], url, **kwargs)
        except httpx.TimeoutException:
            raise ClickUpError(
                "ClickUp request timed out; check the resource before retrying a mutation."
            ) from None
        except httpx.RequestError:
            raise ClickUpError(
                "Could not connect to ClickUp; check connectivity before retrying."
            ) from None
        except (ValueError, TypeError, RuntimeError):
            raise ClickUpError("Could not serialize or send the ClickUp request.") from None
        if not response.content:
            data = None
        else:
            try:
                data = response.json()
            except ValueError:
                data = response.text
        data = self._redact(data)
        if response.is_error or response.is_redirect:
            retry_after = self._redact(response.headers.get("retry-after"))
            reset = self._redact(response.headers.get("x-ratelimit-reset"))
            detail = (
                json.dumps(data, ensure_ascii=True)
                if isinstance(data, (dict, list))
                else str(data or "")
            )
            message = f"ClickUp API returned HTTP {response.status_code}: {detail[:1000]}"
            if response.status_code == 429:
                message += (
                    f". Rate limited; Retry-After={retry_after or 'unavailable'}, "
                    f"X-RateLimit-Reset={reset or 'unavailable'}. Retry explicitly when allowed."
                )
            raise ClickUpError(
                message,
                status_code=response.status_code,
                retry_after=retry_after,
                rate_limit_reset=reset,
            )
        return {"status": response.status_code, "data": data}
