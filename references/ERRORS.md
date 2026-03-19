# Error Handling Reference

All CLI error patterns and recovery steps. SKILL.md delegates here for both
validation errors and setup failures.

---

## Validation Errors

When the CLI exits with code 1 and stdout starts with `Validation failed:`, output the error string exactly as it appears in the terminal. The scripts output safe, user-friendly language. Ask the user to correct the specified fields and offer to regenerate.

---

## Setup Errors

When the CLI fails with anything that does not start with `Validation failed:`, it is
a setup problem. Always explain the command and ask for confirmation before running it.
Retry the generation automatically once the fix is applied.

### `command not found: uv`

uv is not installed.

> "The `uv` package manager is required but not installed. To install it I'll need to
> run the official installer from astral.sh. Shall I proceed?"

If confirmed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### `ModuleNotFoundError` or `No module named`

Python dependencies have not been installed yet.

> "The Python dependencies for doc-generator are not installed. I'll run `uv sync`
> inside the skill directory — this only installs packages listed in `pyproject.toml`.
> Shall I proceed?"

If confirmed:

```bash
uv sync --directory ~/.agents/skills/doc-generator
```

---

### `WeasyPrint could not import some external libraries`

Pango is not installed.

> "doc-generator requires the Pango library, which is missing on this machine.
> On macOS, I'll need to run `brew install pango`. On Ubuntu/Debian, `sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0`.
> Shall I proceed?"

If confirmed (macOS):

```bash
brew install pango
```

If confirmed (Debian/Ubuntu):

```bash
sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
```

---

### `No such file or directory` referencing `scripts/generate.py`

The skill files were not cloned properly.

> "The doc-generator project files are missing. I'll need to clone the repository
> to `~/.agents/skills/doc-generator`. Shall I proceed?"

If confirmed:

```bash
git clone https://github.com/julioccorderoc/doc-generator.git ~/.agents/skills/doc-generator
uv sync --directory ~/.agents/skills/doc-generator
```

---

## Notes

- Multiple dependencies may be missing at once. Each run surfaces one error at a time —
  work through them in order until generation succeeds.
- On macOS, `DYLD_LIBRARY_PATH=/opt/homebrew/lib` is already part of the standard
  invocation in SKILL.md — no additional action needed after installing Pango.
