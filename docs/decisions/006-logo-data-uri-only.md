# 006 — Logo Field Accepts Only Base64 Data URIs

**Status:** Accepted
**Date:** 2026-03-18

## Context

The original `utils/logo.py` accepted either a local file path or an HTTPS URL in the `logo` field of any payload. This created two security problems:

1. **Path traversal** — `_resolve_file()` resolved relative paths against `Path.cwd()` with no boundary check. A payload with `"logo": "../../../../etc/passwd"` would base64-encode an arbitrary local file into the generated PDF.

2. **Unrestricted URL fetch** — `_resolve_url()` made an outbound HTTP request to any URL. In cloud environments, this enables server-side request forgery (SSRF) against metadata endpoints such as `http://169.254.169.254/`.

Both vectors were exploitable by anyone who could influence the JSON payload — including end users interacting with Claude during document generation.

## Decision

`utils/logo.py` accepts **only pre-resolved base64 data URIs** of the form `data:image/<subtype>;base64,<data>`. Any other value raises `ValueError`. `_resolve_file()` and `_resolve_url()` have been removed entirely.

The responsibility for converting a logo source into a data URI moves to the agent layer (Claude), not the CLI:

- If the user provides a logo file path, Claude reads the file using the `Read` tool and encodes it as a data URI before writing the payload.
- The CLI never reads from the local filesystem or makes outbound network requests on behalf of a user-supplied logo value.

This is documented in `SKILL.md` (Invocation §1), `references/purchase_order.md`, `references/invoice.md`, and `references/EXTENDING.md`.

## Consequences

- **File paths and URLs in the `logo` field will raise `ValueError` at render time.** Any existing payload that contains a file path or URL will fail validation.
- **No network calls at generation time.** The CLI remains fully local and air-gap safe.
- **`utils/logo.py` is simpler** — it is now a one-function validation pass, not a resolver.
- **Agents must pre-encode logos.** Claude (or any other agent) must read and base64-encode the image before writing the payload. This is a one-time cost per invocation and is explicit in the skill instructions.
- **Future schema authors** adding a `logo` field to a new doc type should accept `Optional[str]` in the schema and call `resolve_logo()` in the context builder — the function will enforce the data URI constraint at render time.
