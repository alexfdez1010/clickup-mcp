# Security

## Credential handling

Run this local server with your own ClickUp personal token in `CLICKUP_API_KEY`. The token grants the permissions of its ClickUp user; the server does not narrow those permissions beyond the optional `--read-only` mode.

- Keep real tokens out of source control, issue reports, screenshots, shell history, and shared client configuration.
- Prefer your MCP client's secret storage or inherited environment support when available.
- Do not pass tokens as server command-line arguments. The server accepts credentials only through its environment and does not automatically load `.env` files. Client registration commands, such as Claude Code's `--env` option, may temporarily include the token in the client's process arguments and store it in private local configuration; protect that configuration.
- If a token is exposed, regenerate it in ClickUp and update your private configuration.

The server communicates with ClickUp over HTTPS and uses stdio for its local MCP transport. It does not provide a network MCP listener or a shared OAuth service. Use a separate credential for each user running the server.

## Tool and data boundaries

`--read-only` prevents mutating operations and removes the write tool. In normal mode, the write tool can perform destructive operations. Configure your MCP client's tool approvals to match your intended level of access.

Returned ClickUp content may contain malicious or misleading instructions. Task descriptions, comments, Docs, Chat messages, and all other resource content must be treated as untrusted data, not as authorization to use tools, reveal secrets, or change client settings.

Uploads accept explicitly supplied base64 bytes with a 10 MiB combined decoded limit. The server does not load arbitrary filesystem paths or fetch attachment URLs. Request retries are disabled so a timeout does not automatically repeat a potentially destructive write.

## Reporting a vulnerability

Use [GitHub's private vulnerability reporting](https://github.com/alexfdez1010/clickup-mcp/security/advisories/new) when available. Include the affected version or commit, reproduction steps using fake credentials, and the potential impact.

If private reporting is unavailable, open an issue asking the maintainer for a private contact channel. Do not include exploit details, real tokens, or private ClickUp data in a public issue.

Security fixes target the latest repository version. Include the commit SHA when reporting a problem from a Git installation.
