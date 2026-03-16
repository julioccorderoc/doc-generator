# 003 — `--payload` Accepts a File Path, Not Inline JSON

**Status:** Accepted
**Date:** 2026-03-16

## Context

The obvious alternative to `--payload path/to/file.json` is `--payload '{"key": "value"}'` — passing the JSON string directly as a CLI argument. This appears simpler: no temp file required, one fewer step for the calling agent.

The problem is shell quoting. Inline JSON contains double quotes, braces, colons, brackets, and potentially special characters in user-supplied strings (company names, addresses, notes). Correctly quoting a multi-line JSON object for a shell invocation is fragile across:

- Different shells (bash, zsh, fish, PowerShell, cmd.exe)
- Different operating systems
- Agent runtimes that construct the command string programmatically

A single unescaped `"` or `$` in a company name silently corrupts the payload or raises a parse error with a confusing message. The failure mode is non-deterministic and hard to debug.

## Decision

`--payload` accepts only a path to a JSON file. The calling agent writes the payload to a temporary file and passes its path. The script reads and parses the file directly.

```text
# Agent workflow:
# 1. Write payload to a temp file
# 2. Call: uv run python scripts/generate.py --doc_type purchase_order --payload /tmp/payload.json
```

The file path is always unambiguous, shell-safe, and works identically across all platforms and agent runtimes.

## Consequences

- The calling agent must write a temp file before invoking the script. This is one extra step but is trivial for any agent runtime (all can write files).
- Shell quoting issues are eliminated entirely.
- The payload file is a complete record of what was submitted, useful for debugging.
- Inline JSON will never be supported via `--payload`. Agents must always use a file.
