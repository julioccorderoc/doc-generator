# 004 — Use stdlib `argparse` for the CLI; No Framework Dependencies

**Status:** Accepted
**Date:** 2026-03-16

## Context

`click` and `typer` are popular Python CLI frameworks that offer decorator-based argument parsing, automatic help generation, and type coercion. They are ergonomic for interactive development.

This tool's CLI is not interactive. It is invoked by AI agents and automated pipelines with a fixed set of arguments. No prompts, no REPL, no shell completion.

Adding `click` or `typer` introduces:

- An extra pip/uv dependency and its transitive deps
- Potential version conflicts with future additions to the project
- Behavior that differs from stdlib in edge cases (e.g., how errors are reported, how `--help` exits)

The tool's stated goal is to be callable by *any* agent runtime. Every Python 3.11+ environment has `argparse` in the stdlib. There is no environment that has `click` by default.

## Decision

`scripts/generate.py` uses only `argparse` from the stdlib for argument parsing. No CLI framework will be added to the project's dependencies.

The interface is fixed and minimal:

- `--doc_type` (required)
- `--payload` (required)
- `--preview` (optional flag)

Help text is defined via `argparse` `help=` strings and `description=`. Error output goes to stdout (not stderr) with a non-zero exit code so that agent runtimes that only capture stdout receive the error message.

## Consequences

- Zero additional dependencies for the CLI layer.
- `argparse` error messages are slightly less polished than `click`/`typer`, but agents don't display help text to users.
- Adding new arguments to the CLI in future phases requires only `parser.add_argument(...)` — no decorators, no additional types.
- Interactive use cases (tab completion, REPL) are explicitly out of scope and will not be supported.
