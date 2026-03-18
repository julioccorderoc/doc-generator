# doc-generator

![Python](https://img.shields.io/badge/python-3.11+-blue) ![License](https://img.shields.io/github/license/julioccorderoc/doc-generator) ![Stars](https://img.shields.io/github/stars/julioccorderoc/doc-generator?style=social)

A Claude skill and CLI tool that turns a natural language request into a professional PDF business document. Claude handles the conversation; a deterministic script handles rendering. Same input always produces the same PDF.

<!-- DEMO GIF PLACEHOLDER — record via Loom or QuickTime, see content/screen_recording.md -->
<!-- ![doc-generator demo](assets/demo.gif) -->

```bash
# Install the skill — one command
npx skills add julioccorderoc/doc-generator
```

Then just ask Claude:

> "I need a PO for PureSource — 250kg whey protein at $8.40/kg, net 30, FedEx Ground."

Claude collects what it needs, confirms, and drops a clean PDF in your `output/` folder. No forms, no SaaS, no copy-paste.

> New doc type ideas or contributions welcome — adding one requires [five files, nothing else](#extending).

---

## What it looks like

<!-- SCREENSHOT PLACEHOLDER — clean generated purchase order -->
<!-- ![Purchase Order](assets/screenshot_po.png) -->

<!-- SCREENSHOT PLACEHOLDER — clean generated invoice -->
<!-- ![Invoice](assets/screenshot_invoice.png) -->

*Replace placeholders above with screenshots from your `output/` folder once generated.*

---

## Supported Document Types

| Slug | Document | Description |
| --- | --- | --- |
| `purchase_order` | Purchase Order | Buyer-to-vendor authorization for goods or services at agreed prices and terms |
| `invoice` | Invoice | Issuer-to-client payment request for goods delivered or services rendered |
| `request_for_quotation` | Request for Quotation (RFQ) | Buyer-to-vendor specification document requesting a price; no monetary values |

On the roadmap: delivery notes, packing slip, quotes.

---

## How It Works

1. **Claude collects data** — asks for required fields in a single pass, applies smart defaults, never asks for computed values.
2. **Claude writes a payload file** — JSON at a temp path. No inline JSON, no shell quoting issues.
3. **Claude invokes the CLI** — `uv run python scripts/generate.py --doc_type <type> --payload <path>`.
4. **The script renders the PDF** — Pydantic validates, Python computes, Jinja2 renders, WeasyPrint writes. No model in the render path.
5. **Claude reports the result** — output path, grand total, balance due, or a plain-language validation error.

<!-- SCREENSHOT PLACEHOLDER — Claude success response showing output path and grand total -->
<!-- ![Claude output](assets/screenshot_result.png) -->

---

## Full Setup (CLI + skill in one step)

The skill alone lets Claude orchestrate the workflow. The CLI is what actually renders the PDF — it needs to be on your machine.

```bash
curl -fsSL https://raw.githubusercontent.com/julioccorderoc/doc-generator/master/install.sh | bash
```

Or clone and run directly:

```bash
git clone https://github.com/julioccorderoc/doc-generator.git
cd doc-generator && ./install.sh
```

The installer clones the repo, installs Python dependencies (`uv sync`), installs Pango on macOS, and writes a path-correct skill to `~/.claude/skills/doc-generator/`. Re-running is idempotent.

**To update the skill after changes:**

```bash
npx skills update -g
```

> See [SKILL.md](SKILL.md) for the full skill definition: trigger conditions, data collection protocol, and output presentation format.

---

## Stack

| Library | Role |
| --- | --- |
| [WeasyPrint](https://weasyprint.org) | HTML/CSS → PDF renderer. No headless browser, no Chromium. |
| [Jinja2](https://jinja.palletsprojects.com) | Templating engine. Templates receive pre-formatted strings — no logic inside. |
| [Pydantic v2](https://docs.pydantic.dev) | Schema validation and computed fields (`subtotal`, `grand_total`, etc.). |
| [uv](https://github.com/astral-sh/uv) | Dependency management and script runner. Reproducible environments with a lockfile. |

---

## CLI Reference

For agents or direct use:

```text
uv run python scripts/generate.py --doc_type <type> --payload <path> [--preview]
```

| Argument | Required | Description |
| --- | --- | --- |
| `--doc_type` | Yes | Document type slug (`purchase_order`, `invoice`, `request_for_quotation`). |
| `--payload` | Yes | Path to a JSON file. File path only — not inline JSON. |
| `--preview` | No | Opens the PDF with the OS default viewer after generation. Silent no-op in headless environments. |

**Exit codes:**

| Outcome | Exit code | stdout |
| --- | --- | --- |
| Success | `0` | Output path, e.g. `output/purchase_order_20260316_0001.pdf` |
| Validation error | `1` | Structured error — which fields failed and why |
| Unknown `doc_type` | `1` | List of registered doc type slugs |

No interactive prompts. No assumed environment variables. Agents capture stdout and check the exit code.

> Full platform-agnostic interface contract: [CLAUDE.md](CLAUDE.md).

---

## Running Locally

**macOS prerequisites:**

```bash
uv sync
brew install pango   # WeasyPrint system dependency — once only
```

**Generate a document:**

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order \
  --payload tests/fixtures/sample_po.json \
  --preview
```

**Test validation error output:**

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order \
  --payload tests/fixtures/invalid_po.json
```

**Run the test suite** (no Pango or display needed):

```bash
uv run pytest
```

Full field references — all optional fields, validation rules, and example payloads:

- [references/purchase_order.md](references/purchase_order.md)
- [references/invoice.md](references/invoice.md)
- [references/request_for_quotation.md](references/request_for_quotation.md)

---

## Extending

Adding a new document type requires five files — nothing else changes:

```text
1. references/<doc_type>.md      — field definitions, validation rules, computed fields, layout notes
2. schemas/<doc_type>.py         — Pydantic v2 model derived from the reference
3. templates/<doc_type>.html     — Jinja2 template extending base.html
4. builders/<doc_type>.py        — context builder function
5. builders/__init__.py          — one DocTypeConfig entry added to REGISTRY
```

`generate.py`, `base.html`, `style.css`, and the core generation engine are never modified when adding a doc type.

See [references/EXTENDING.md](references/EXTENDING.md) for the full developer guide.

---

## Why This Skill Is Safe to Install

| Property | Detail |
| --- | --- |
| **Deterministic** | Same JSON input always produces the same PDF. No randomness, no model calls in the render path. |
| **Fully local** | Runs on your machine. No outbound network calls at generation time. |
| **No paid services** | WeasyPrint, Jinja2, and Pydantic are all open-source. No API keys required. |
| **No credential access** | The script reads only the payload file you pass it. It does not touch environment variables, secrets, or system files. |
| **Auditable** | The render path is a single script: [scripts/generate.py](scripts/generate.py). Templates: [templates/](templates/). Schemas: [schemas/](schemas/). |

---

## Project Structure

Key directories — full detail in [CLAUDE.md](CLAUDE.md):

```text
doc-generator/
├── CLAUDE.md          ← Agent entry point: CLI contract, conventions, design decisions
├── SKILL.md           ← Claude skill definition
├── scripts/           ← CLI entrypoint (generate.py)
├── schemas/           ← Pydantic v2 models per doc type
├── builders/          ← Context builders + REGISTRY
├── templates/         ← Jinja2 templates extending base.html
├── assets/            ← style.css + per-doc-type CSS
├── references/        ← Source-of-truth specs + EXTENDING.md + DESIGN_SYSTEM.md
└── tests/fixtures/    ← Valid and invalid sample payloads
```

---

## Contributing

Contributions welcome. The most useful things to add:

- **New document types** — follow the five-step pattern in [references/EXTENDING.md](references/EXTENDING.md). Each doc type is self-contained.
- **Bug fixes** — check [docs/decisions/](docs/decisions/) before changing any architectural pattern; a decision record may explain the constraint.

When in doubt, read the reference file for the doc type you are modifying first. The reference is the source of truth — not the code.
