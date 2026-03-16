# Security Review — doc-generator

**Date:** 2026-03-16
**Author:** Claude Sonnet 4.6 (Anthropic)
**Scope:** Full codebase review (`master` branch, up to date with `origin/master`)
**Method:** Static analysis — data flow tracing from all user inputs to sensitive operations

---

## Summary

No actionable vulnerabilities found. Two path traversal candidates were identified and ruled out as false positives after evaluating the tool's threat model. The codebase demonstrates consistently secure practices for a local CLI tool.

---

## Findings

### Finding 1: Path Traversal via `logo` Field — FALSE POSITIVE

**File:** `utils/logo.py`
**Category:** Path Traversal (CWE-22)
**Initial Confidence:** 9/10 → **Ruled out**

The `_resolve_file()` function joins a user-supplied logo path with `Path.cwd()` without normalizing `../` sequences. An attacker who controls the JSON payload could theoretically supply `logo: "../../../../etc/passwd"` to read an arbitrary file and have it base64-encoded into the generated PDF.

**Why ruled out:** Exploiting this requires the attacker to (a) have code execution to write the malicious JSON file to disk, and (b) invoke the CLI with that file as `--payload`. An attacker with those capabilities already has direct filesystem access — this path adds no new attack surface. The finding does not cross a security boundary.

---

### Finding 2: Path Traversal via `--payload` CLI Argument — FALSE POSITIVE

**File:** `scripts/generate.py` (payload loading section)
**Category:** Path Traversal (CWE-22)
**Initial Confidence:** 8/10 → **Ruled out**

The `--payload` argument accepts any file path without restricting traversal sequences. An attacker controlling the CLI invocation could pass `../sensitive.json` to read arbitrary JSON files.

**Why ruled out:** CLI flags are trusted inputs in this tool's threat model. The tool is designed to be invoked by agents with shell access — if an attacker controls the CLI invocation, they already have full filesystem access. This is a non-issue for a local CLI tool with no network-exposed attack surface. Decision record [003](decisions/003-file-path-payload.md) explicitly acknowledges that agents write temporary files and pass the path.

---

## Positive Findings

| Area | Detail |
|---|---|
| Template rendering | Jinja2 autoescape is enabled — all user content is HTML-escaped before rendering |
| Subprocess calls | `preview.py` uses `subprocess.run()` with a list argument, no `shell=True` — no command injection |
| Deserialization | Only `json.loads()` is used — no pickle, marshal, or unsafe YAML |
| WeasyPrint input | Receives a fully pre-rendered HTML string — no injection path into the renderer |
| Schema validation | All payloads are validated against Pydantic v2 models before any rendering occurs |

---

## Threat Model Notes

This tool has a narrow, well-defined threat model:

- **Invocation:** Local CLI only. No HTTP endpoints, no daemon, no network exposure.
- **Callers:** Trusted AI agents (Claude, Cursor, Gemini, etc.) or direct human invocation.
- **Output:** A deterministic PDF written to `output/`. No network egress, no database writes, no side effects.
- **Privilege:** Runs as the invoking user with no elevated permissions.

Vulnerabilities that require controlling CLI arguments or writing files to disk are out of scope under this threat model, as those capabilities imply the attacker already has equivalent access.

---

## Recommendation

No immediate action required. Consider adding the following as a future hardening measure (not a security fix):

- In `utils/logo.py`, add `path.resolve()` before reading the file, and document that the logo path must point to a valid image. This is a defense-in-depth measure for cases where the tool is eventually exposed via a wrapper API.
