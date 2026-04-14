# 003 — `--payload` Accepts a File Path, Not Inline JSON

**Status:** Accepted
**Date:** 2026-03-16

## Context

Alternative: `--payload '{"key": "value"}'` — passing JSON string directly as CLI argument. Appears simpler: no temp file, one fewer step.

Problem: shell quoting. Inline JSON contains double quotes, braces, colons, brackets, plus special characters in user-supplied strings (company names, addresses, notes). Correctly quoting multi-line JSON for shell invocation is fragile across:

- Different shells (bash, zsh, fish, PowerShell, cmd.exe)
- Different operating systems
- Agent runtimes constructing command strings programmatically

Single unescaped `"` or `$` in a company name silently corrupts payload or raises confusing parse error. Failure mode is non-deterministic and hard to debug.

## Decision

`--payload` accepts only a path to a JSON file. Calling agent writes payload to temp file and passes path. Script reads and parses file directly.

```text
# Agent workflow:
# 1. Write payload to a temp file
# 2. Call: uv run python scripts/generate.py --doc_type purchase_order --payload /tmp/payload.json
```

File path is always unambiguous, shell-safe, works identically across all platforms and agent runtimes.

## Consequences

- Calling agent must write temp file before invoking. One extra step but trivial for any agent runtime (all can write files).
- Shell quoting issues eliminated entirely.
- Payload file is a complete record of what was submitted, useful for debugging.
- Inline JSON will never be supported via `--payload`. Agents must always use a file.
