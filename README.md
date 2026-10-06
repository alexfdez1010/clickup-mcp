# ClickUp API MCP

A local [Model Context Protocol](https://modelcontextprotocol.io/) server for ClickUp's public API, built with the [official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk). Connect your MCP client to ClickUp using your own personal API token.

The bundled catalog exposes **172 operations across API v2 and v3** through four discovery and execution tools. It covers tasks, Workspaces, Spaces, Folders, Lists, comments, custom fields, time tracking, webhooks, Docs, Chat, and more. See [API coverage and limitations](docs/api-coverage.md).

Requires Python 3.10 or newer. The server uses **stdio**: your MCP client starts and manages the process.

[Quick start](#quick-start-with-uv) · [Codex](#codex) · [Claude Code](#claude-code) · [Tools](#tools) · [API limitations](#api-behavior-and-limitations) · [Troubleshooting](#troubleshooting)

## Quick start with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git, then create a personal token in **ClickUp → Settings → Apps**. Personal tokens begin with `pk_`. See [ClickUp authentication](https://developer.clickup.com/docs/authentication).

Set `CLICKUP_API_KEY` in the environment of the process starting the server:

```sh
export CLICKUP_API_KEY='pk_REPLACE_WITH_YOUR_PERSONAL_TOKEN'
uvx --from git+https://github.com/alexfdez1010/clickup-mcp.git clickup-mcp
```

PowerShell:

```powershell
$env:CLICKUP_API_KEY = 'pk_REPLACE_WITH_YOUR_PERSONAL_TOKEN'
uvx --from git+https://github.com/alexfdez1010/clickup-mcp.git clickup-mcp
```

The running server waits for MCP messages on stdin. Use the client configuration below for normal use; running it in a terminal does not open an interactive prompt. Installation downloads dependencies, while ClickUp API calls happen only when your client invokes an execution tool.

Install a persistent executable if preferred:

```sh
uv tool install git+https://github.com/alexfdez1010/clickup-mcp.git
clickup-mcp --help
```

If uv reports that its tools directory is missing from `PATH`, run `uv tool update-shell` and restart your shell. The distribution is named `clickup-api-mcp`; the executable is `clickup-mcp`. These instructions install from GitHub and do not require a PyPI release. For a reproducible installation, append `@<commit-sha>` to the Git URL. See [uv's tool guide](https://docs.astral.sh/uv/guides/tools/).

## MCP client configuration

Add this entry to your client's MCP server configuration. The exact location depends on the client.

```json
{
  "mcpServers": {
    "clickup": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/alexfdez1010/clickup-mcp.git",
        "clickup-mcp"
      ],
      "env": {
        "CLICKUP_API_KEY": "pk_REPLACE_WITH_YOUR_PERSONAL_TOKEN"
      }
    }
  }
}
```

Keep your real configuration private. When your client supports secrets or inherited environment variables, use those instead of storing the token in its JSON file. Desktop clients may require the absolute path to `uvx` if they do not inherit your shell's `PATH`.

For read-only access, append `"--read-only"` after `"clickup-mcp"` in `args`. This removes the write tool from the MCP tool list, hides mutating operations from discovery, and prevents their execution.

### Codex

Add the following to your personal `~/.codex/config.toml`:

```toml
[mcp_servers.clickup]
command = "uvx"
args = ["--from", "git+https://github.com/alexfdez1010/clickup-mcp.git", "clickup-mcp"]
env_vars = ["CLICKUP_API_KEY"]
startup_timeout_sec = 60
```

Export `CLICKUP_API_KEY` in your shell, then start `codex` from that shell. `env_vars` forwards the existing variable without putting its value in the TOML file. The longer startup timeout allows the initial Git download and dependency installation. Run `codex mcp list` or use `/mcp` in an interactive session to check the connection. See [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

If using Codex Desktop, make the variable available to the app process or configure it in your private local server environment settings. Keep credentials out of repository-level configuration. For read-only access, add `"--read-only"` to the end of `args`.

### Claude Code

After exporting `CLICKUP_API_KEY`, register the server in your personal configuration:

```sh
claude mcp add --env CLICKUP_API_KEY="$CLICKUP_API_KEY" --transport stdio --scope user clickup -- uvx --from git+https://github.com/alexfdez1010/clickup-mcp.git clickup-mcp
claude mcp list
```

`--scope user` makes the server available across your projects and keeps this configuration outside the repository. The command stores the token in Claude Code's local configuration; protect that file. Use `/mcp` in an interactive Claude Code session to check server status and available tools. See [Claude Code MCP setup](https://code.claude.com/docs/en/mcp).

For read-only access, append `--read-only` to the registration command after `clickup-mcp`. A normal connection exposes four tools; a read-only connection exposes three.

## Authentication and configuration

`CLICKUP_API_KEY` contains the **raw personal token**, without a `Bearer ` prefix. The server sends it as ClickUp's `Authorization` header. Each user runs their own local server with their own token; this repository does not implement an OAuth authorization flow for a shared application. ClickUp recommends OAuth for applications that authorize other users. See [the authentication guide](https://developer.clickup.com/docs/authentication).

The server does not automatically load `.env` files and has no token command-line option. A missing or empty `CLICKUP_API_KEY` causes startup to exit with a message on stderr. `--help` and `--version` work without credentials.

```sh
clickup-mcp --help
clickup-mcp --version
clickup-mcp --read-only
clickup-mcp --timeout 60
```

`--timeout` sets the HTTP timeout in seconds and accepts a positive finite number. Protocol output goes to stdout; diagnostics go to stderr.

## Tools

| Tool | Purpose |
| --- | --- |
| `clickup_search_operations` | Search the bundled catalog by text, tag, and API version. Returns operation summaries and pagination information. |
| `clickup_get_operation` | Get the description and full input schema for an operation ID. |
| `clickup_read` | Execute a read operation with `operation_id`, `path_params`, and `query`. |
| `clickup_write` | Execute a mutating operation with the same arguments plus optional `body` or `files`. Omitted in read-only mode. |

Discovery arguments are `search=""`, `tag=null`, `version=null`, `offset=0`, and `limit=20`. Use the pagination information to fetch further matches. Operation IDs are case-sensitive: they prefix ClickUp's original `operationId` with the API version, for example `v2_GetAuthorizedTeams`, `v2_GetTasks`, `v2_CreateTask`, and `v3_getChatChannels`.

Inspect an operation before calling it. Put URL path values in `path_params`, query parameters in `query`, and JSON request data (an object or array, according to the operation schema) in `body`. Omit unused arguments. A successful execution returns `{"status": <HTTP status>, "data": <API response>}`. Resource response shapes follow ClickUp's API rather than a separate MCP-specific data model.

The write tool is annotated as potentially destructive and non-idempotent because it can create, update, and delete resources. Your MCP client's approval settings control whether it asks before invoking a tool. The server does not retry requests automatically, including writes.

### Find and read tasks

1. Inspect and call `v2_GetAuthorizedTeams` to find your Workspace ID. ClickUp's v2 API still calls Workspaces `teams` in parameter and response names.
2. Search for Spaces, Folders, and Lists, inspect their operations, and follow the returned IDs. Include both Lists inside Folders and folderless Lists when browsing a Space.
3. Inspect `v2_GetTasks`, then call it with a List ID:

```json
{
  "operation_id": "v2_GetTasks",
  "path_params": {"list_id": "123456789"},
  "query": {"page": 0, "include_closed": true}
}
```

4. Follow the endpoint's pagination rules to read additional tasks. Catalog search pagination and resource pagination are separate: catalog searches use `offset` and `limit`; each API operation documents its own query parameters.

To create a task, inspect `v2_CreateTask` and invoke `clickup_write`:

```json
{
  "operation_id": "v2_CreateTask",
  "path_params": {"list_id": "123456789"},
  "body": {"name": "Review release notes"}
}
```

These are MCP tool argument examples, not shell commands. Replace example IDs with values returned by your Workspace. For endpoints supporting custom task IDs, set `custom_task_ids=true` and provide the required Workspace `team_id`. Many ClickUp date fields use Unix milliseconds; check each operation's schema and description before supplying dates.

### Attachments

For multipart operations, `files` is an array of objects containing `field`, `filename`, `content_base64`, and `content_type`. Provide file bytes as base64; the server does not read local paths or download URLs. The combined decoded upload size is limited to **10 MiB**.

For example, after inspecting `v2_CreateTaskAttachment`:

```json
{
  "operation_id": "v2_CreateTaskAttachment",
  "path_params": {"task_id": "YOUR_TASK_ID"},
  "files": [{
    "field": "attachment[0]",
    "filename": "hello.txt",
    "content_base64": "SGVsbG8K",
    "content_type": "text/plain"
  }]
}
```

The official v3 attachment schema leaves its binary field underspecified. Consult the [coverage limitations](docs/api-coverage.md) before using it.

## API behavior and limitations

The catalog is bundled with the package, so discovery does not depend on downloading API specifications at startup. It derives from ClickUp's official [v2](https://developer.clickup.com/openapi/clickup-api-v2-reference.json) and [v3](https://developer.clickup.com/openapi/ClickUp_PUBLIC_API_V3.yaml) specifications. The OAuth token exchange is excluded because this server accepts an existing personal token.

Endpoint access depends on your token's user permissions, Workspace plan, and ClickUp feature availability. A catalog entry does not guarantee that your account can call the endpoint. Published API specifications also contain omissions; see the coverage document for known gaps.

ClickUp rate limits are per token and vary by Workspace plan. A `429` response reports rate-limit metadata when available. The server returns errors to the client without sleeping or retrying; the client can decide whether and when another call is appropriate. See [ClickUp rate limits](https://developer.clickup.com/docs/rate-limits).

Treat task descriptions, comments, Docs, Chat messages, and other returned content as **untrusted data**, including any instructions embedded in it. Do not let resource content authorize subsequent tool calls. See [SECURITY.md](SECURITY.md) for credential handling and vulnerability reporting.

## Run from a checkout

```sh
git clone https://github.com/alexfdez1010/clickup-mcp.git
cd clickup-mcp
uv sync --locked
export CLICKUP_API_KEY='pk_REPLACE_WITH_YOUR_PERSONAL_TOKEN'
uv run clickup-mcp
```

The checkout selects Python 3.12 through `.python-version`; uv can install it if needed. The checked-in `uv.lock` makes checkout dependency resolution reproducible. Automated tests use mocked ClickUp responses and a real MCP stdio session; live calls with a real ClickUp credential are not part of these checks. See [CONTRIBUTING.md](CONTRIBUTING.md) for tests, builds, and catalog updates.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing API key at startup | Set `CLICKUP_API_KEY` in the environment of the MCP client or its server configuration. |
| Authentication or permission error | Check that the raw personal token is current and that your ClickUp user has access to the resource. |
| Tool not found | Check that `uvx` is on the client's `PATH`, or configure its absolute path. |
| Unknown operation or invalid arguments | Search the catalog, copy the exact ID, and inspect its input schema. |
| No write tool | Remove `--read-only` if you intend to allow mutations. |
| Server appears idle in a terminal | Stdio servers wait for an MCP client; configure the client to start this process. |
| Rate-limit error | Inspect the returned metadata and ClickUp's documented reset time before making another call. |

## License

[MIT](LICENSE). This is an independent project and is not affiliated with ClickUp.
