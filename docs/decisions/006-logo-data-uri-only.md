# 006 — Logo Field Accepts Only Base64 Data URIs

**Status:** Accepted
**Date:** 2026-03-18

## Context

Original `utils/logo.py` accepted local file paths or HTTPS URLs in `logo` field. Two security problems:

1. **Path traversal** — `_resolve_file()` resolved relative paths against `Path.cwd()` with no boundary check. Payload with `"logo": "../../../../etc/passwd"` would base64-encode arbitrary local file into PDF.

2. **Unrestricted URL fetch** — `_resolve_url()` made outbound HTTP request to any URL. In cloud environments, enables SSRF against metadata endpoints like `http://169.254.169.254/`.

Both exploitable by anyone who could influence JSON payload — including end users interacting with Claude during document generation.

## Decision

`utils/logo.py` accepts **only pre-resolved base64 data URIs** of form `data:image/<subtype>;base64,<data>`. Any other value raises `ValueError`. `_resolve_file()` and `_resolve_url()` removed entirely.

Responsibility for converting logo source into data URI moves to agent layer (Claude), not CLI:

- If user provides logo file path, Claude reads file using `Read` tool and encodes as data URI before writing payload.
- CLI never reads from local filesystem or makes outbound network requests for user-supplied logo values.

Documented in `SKILL.md` (Invocation), `references/purchase_order.md`, `references/invoice.md`, and `references/EXTENDING.md`.

## Consequences

- **File paths and URLs in `logo` field raise `ValueError` at render time.** Any existing payload with file path or URL fails validation.
- **No network calls at generation time.** CLI remains fully local and air-gap safe.
- **`utils/logo.py` is simpler** — one-function validation pass, not a resolver.
- **Agents must pre-encode logos.** Claude (or any agent) must read and base64-encode image before writing payload. One-time cost per invocation, explicit in skill instructions.
- **Future schema authors** adding `logo` field should accept `Optional[str]` in schema and call `resolve_logo()` in context builder — function enforces data URI constraint at render time.
