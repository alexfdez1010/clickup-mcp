# Contributing

Contributions are welcome. Keep code, documentation, commit messages, and examples in English. For large changes, open an issue describing the problem and proposed behavior before implementation.

## Development setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git, then:

```sh
git clone https://github.com/alexfdez1010/clickup-mcp.git
cd clickup-mcp
uv sync --locked
```

The checkout uses Python 3.12. The package supports Python 3.10 and newer; CI checks Python 3.10, 3.12, and 3.14. Commit `uv.lock` whenever an intentional dependency change requires an update.

## Checks

Run the same checks as CI:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
```

Use `uv run ruff format .` to apply formatting. Tests should use mocked HTTP responses and exercise observable behavior, including failures. Do not require a real ClickUp token or make live API calls in automated tests. Never commit credentials, private resource content, or recordings containing them.

When manually running the server, provide `CLICKUP_API_KEY` in the environment and use an MCP client. Prefer `--read-only` for exploratory validation. Stdio stdout must contain only MCP protocol traffic; send diagnostics to stderr.

## Update the API catalog

The catalog is generated from ClickUp's official public API specifications. Regenerate it using:

```sh
uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD
uv run pytest
```

Replace `YYYY-MM-DD` with the date you fetch the source specifications. The generated coverage document records the same snapshot date.

Review the generated changes before committing. Verify operation counts, IDs, methods, paths, required parameters, request schemas, multipart handling, and exclusions. Update [api-coverage.md](docs/api-coverage.md) and README counts when coverage changes. Discovery must continue to work from the bundled catalog without network access at startup.

ClickUp's published schemas can be incomplete. Document narrowly scoped fixes and their official sources. Do not silently invent fields or claim endpoint support beyond what the transport and schema validation can handle.

## Pull requests

Explain the problem, resulting behavior, and validation in the PR description. Keep unrelated changes separate. Add regression coverage for functional changes where it proves meaningful behavior, and update usage documentation when inputs or installation change.

Check that the wheel contains the bundled catalog and that its `clickup-mcp` entry point works. Run `--help` and `--version` without credentials. Authentication must remain environment-based; never introduce token logging or command-line token arguments.

Report vulnerabilities through the process in [SECURITY.md](SECURITY.md), without posting secrets publicly.
