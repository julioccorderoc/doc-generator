# doc-generator

A Claude skill and CLI tool for generating professional PDF business documents — purchase orders, invoices, and more. Claude (or any agent) handles data collection conversationally; the script handles rendering. Same input always produces the same PDF.

---

## Install as a Claude Skill

```bash
npx skills add julioccorderoc/doc-generator
```

The [`npx skills`](https://github.com/vercel-labs/skills) CLI clones the repo and installs the skill using a symlink, so it stays connected to this repository.

**To update to the latest version at any time:**

```bash
npx skills update
```

Once installed, Claude will automatically generate purchase orders and invoices when you ask — collecting the required data in a single conversational pass, then invoking the CLI and presenting the output path and key figures.

> See [SKILL.md](SKILL.md) for the full skill definition: trigger conditions, data collection protocol per document type, and output presentation format.

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

## Supported Document Types

| Slug | Document | Description |
| --- | --- | --- |
| `purchase_order` | Purchase Order | Buyer-to-vendor authorization for goods or services at agreed prices and terms |
| `invoice` | Invoice | Issuer-to-client payment request for goods delivered or services rendered |

---

## Stack

| Library | Role |
| --- | --- |
| [WeasyPrint](https://weasyprint.org) | HTML/CSS → PDF renderer. No headless browser, no Chromium. |
| [Jinja2](https://jinja.palletsprojects.com) | Templating engine. Templates receive pre-formatted strings — no logic inside. |
| [Pydantic v2](https://docs.pydantic.dev) | Schema validation and computed fields (`subtotal`, `grand_total`, etc.). |
| [uv](https://github.com/astral-sh/uv) | Dependency management and script runner. Reproducible environments with a lockfile. |

---

## How It Works

1. **Claude collects data** — asks for required fields in a single pass, applies smart defaults, never asks for computed values.
2. **Claude writes a payload file** — a JSON file at a temp path. No inline JSON, no shell quoting issues.
3. **Claude invokes the CLI** — `uv run python scripts/generate.py --doc_type <type> --payload <path>`.
4. **The script renders the PDF** — Pydantic validates, Python computes, Jinja2 renders, WeasyPrint writes. No model involved.
5. **Claude reports the result** — output path, grand total, balance due, or a translated validation error.

---

## CLI Reference

For agents or direct use:

```text
uv run python scripts/generate.py --doc_type <type> --payload <path> [--preview]
```

| Argument | Required | Description |
| --- | --- | --- |
| `--doc_type` | Yes | Document type slug (`purchase_order`, `invoice`). |
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

Full field references — all optional fields, validation rules, and example payloads with expected computed output:

- [references/purchase_order.md](references/purchase_order.md)
- [references/invoice.md](references/invoice.md)

---

## Extending

Adding a new document type requires four files — nothing else changes:

```text
1. references/<doc_type>.md      — field definitions, validation rules, computed fields, layout notes
2. schemas/<doc_type>.py         — Pydantic v2 model derived from the reference
3. templates/<doc_type>.html     — Jinja2 template extending base.html
4. scripts/generate.py           — one entry added to the REGISTRY dict
```

`base.html`, `style.css`, and the core generation engine are never modified when adding a doc type.

See [references/EXTENDING.md](references/EXTENDING.md) for the full developer guide.

---

## Project Structure

```text
doc-generator/
│
├── CLAUDE.md                    ← Agent entry point: CLI contract, conventions, design decisions
├── SKILL.md                     ← Claude skill definition: triggers, data collection, invocation
│
├── scripts/
│   └── generate.py              ← CLI entrypoint — the full render path in one file
│
├── schemas/
│   ├── base.py                  ← Shared types and mixins
│   ├── purchase_order.py        ← Pydantic v2 schema for Purchase Orders
│   └── invoice.py               ← Pydantic v2 schema for Invoices
│
├── templates/
│   ├── base.html                ← Shared page layout
│   ├── purchase_order.html      ← PO Jinja2 template
│   └── invoice.html             ← Invoice Jinja2 template
│
├── assets/
│   └── style.css                ← Base stylesheet (CSS custom properties only)
│
├── references/
│   ├── purchase_order.md        ← Source of truth for the purchase_order doc type
│   ├── invoice.md               ← Source of truth for the invoice doc type
│   ├── EXTENDING.md             ← Developer guide for adding new doc types
│   └── DESIGN_SYSTEM.md         ← Visual source of truth: palette, typography, totals design, theming
│
├── tests/
│   └── fixtures/
│       ├── sample_po.json       ← Valid PO payload
│       ├── invalid_po.json      ← PO with missing required fields (expected: validation error)
│       ├── sample_invoice.json             ← Valid Invoice payload
│       ├── sample_invoice_contractor.json ← Individual contractor invoice (unpaid)
│       └── invalid_invoice.json           ← Invoice with missing required fields
│
├── output/                      ← Generated PDFs (.gitignored)
│
└── docs/
    ├── PRD.md                   ← Full product requirements
    └── decisions/               ← Technical decision records (ADRs)
```

---

## Contributing

Contributions welcome. The most useful things to add:

- **New document types** — follow the four-step pattern in [references/EXTENDING.md](references/EXTENDING.md). Each doc type is self-contained.
- **Bug fixes** — check [docs/decisions/](docs/decisions/) before changing any architectural pattern; a decision record may explain the constraint.
- **New document types for the skill** — update [SKILL.md](SKILL.md) trigger conditions and data collection protocol alongside the new doc type.

When in doubt, read the reference file for the doc type you are modifying first. The reference is the source of truth — not the code.
