# 004 — Use stdlib `argparse` for the CLI; No Framework Dependencies

**Status:** Accepted
**Date:** 2026-03-16

## Context

`click` and `typer` offer decorator-based argument parsing, auto help generation, type coercion. Ergonomic for interactive development.

This tool's CLI is not interactive. Invoked by AI agents and automated pipelines with fixed arguments. No prompts, no REPL, no shell completion.

Adding `click` or `typer` introduces:

- Extra pip/uv dependency + transitive deps
- Potential version conflicts with future additions
- Behavior differing from stdlib in edge cases (error reporting, `--help` exit)

Goal: callable by *any* agent runtime. Every Python 3.11+ environment has `argparse` in stdlib. No environment has `click` by default.

## Decision

`scripts/generate.py` uses only `argparse` from stdlib. No CLI framework added to dependencies.

Interface is fixed and minimal:

- `--doc_type` (required)
- `--payload` (required)
- `--preview` (optional flag)

Help text via `argparse` `help=` and `description=`. Error output goes to stdout (not stderr) with non-zero exit code so agent runtimes capturing only stdout receive error messages.

## Consequences

- Zero additional dependencies for CLI layer.
- `argparse` error messages slightly less polished than `click`/`typer`, but agents don't display help text to users.
- Adding new arguments requires only `parser.add_argument(...)` — no decorators, no additional types.
- Interactive use cases (tab completion, REPL) explicitly out of scope and unsupported.
