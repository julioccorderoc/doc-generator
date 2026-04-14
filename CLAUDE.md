# doc-generator

A deterministic, schema-driven PDF generation tool for business documents (Purchase Orders, Invoices, Requests for Quotation, etc.). It is invocable by **any AI agent** that can execute shell commands — Claude, Cursor, Gemini, Codex, or any other tool. No LLM is involved in rendering. Same input always produces the same PDF.

---

## How to Run Locally

```bash
# Install Python dependencies
uv sync

# macOS system dependency — install once via Homebrew:
# brew install pango
# Ubuntu/Debian system dependency:
# sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
# WeasyPrint requires Pango/GObject. On macOS the dylibs are in /opt/homebrew/lib/,
# which is not on the default dyld search path. Prefix every uv run with:
# DYLD_LIBRARY_PATH=/opt/homebrew/lib

# Generate a Purchase Order from a JSON payload
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload tests/fixtures/sample_po.json

# Same, but open the PDF immediately after generation
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload tests/fixtures/sample_po.json --preview

# Generate an Invoice
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type invoice --payload tests/fixtures/sample_invoice.json --preview

# Generate a Request for Quotation
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type request_for_quotation --payload tests/fixtures/sample_rfq.json --preview

# Test validation error output (non-zero exit code, structured error to stdout)
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload tests/fixtures/invalid_po.json
```

---

## CLI Contract (Platform-Agnostic Interface)

Any agent invoking this tool must use the following interface. This is the **complete** contract — there are no interactive prompts, no assumed environment variables, and no implicit state.

```text
uv run python scripts/generate.py --doc_type <type> --payload <path> [--preview] [--save_payload]
```

| Argument | Required | Description |
|---|---|---|
| `--doc_type` | Yes | Document type slug. Must match a registered type (e.g. `purchase_order`, `invoice`, `request_for_quotation`). |
| `--payload` | Yes | Absolute or relative path to a JSON file containing the document data. **File path only** — not inline JSON. This avoids shell escaping issues and lets agents write a temp file before invoking. |
| `--preview` | No | If provided, opens the generated PDF using the OS default viewer after generation. Gracefully no-ops in headless environments (no display, CI). |
| `--output_name` | No | Custom filename stem. If provided, output is `<doc_type>_<name>.pdf`. Defaults to date + sequential counter auto-naming. |
| `--output_dir` | No | Directory to save the generated PDF. Defaults to `<project_root>/output/`. Pass `$(pwd)` to save in the caller's working directory. |
| `--save_payload` | No | If provided, saves the validated payload (with all computed fields) as a `.json` file alongside the PDF, using the same filename stem. |

**On success:** Writes the PDF to the target directory (default `<project_root>/output/`) and prints the **absolute** output path to stdout. Exit code `0`. Agents must use this path directly — never prepend the working directory. If `--save_payload` was passed, a `.json` file with the same stem is also written.

**On validation error:** Prints a structured, human-readable error to stdout describing which fields failed and why. Exit code `1`. No PDF is written.

**On unknown doc_type:** Prints a list of registered doc types to stdout. Exit code `1`.

Agents should capture stdout and check the exit code to determine success or failure.

---

## Folder Structure

```text
doc-generator/
│
├── CLAUDE.md                    ← You are here. Entry point for all AI agents.
├── SKILL.md                     ← Claude-specific skill instructions (orchestration layer: trigger conditions, invocation, error relay — delegates data collection detail to references/<doc_type>.md) — uses ~/.agents/skills/doc-generator as the canonical install path
│
├── .claude/
│   └── settings.json            ← Pre-approved permissions: Write(/tmp/) + Bash CLI invocation (no prompts for team)
│
├── .github/
│   └── workflows/
│       └── sync-skill.yml       ← Auto-opens PR to vercel-labs/agent-skills when SKILL.md changes on master
│
├── pyproject.toml               ← uv project manifest with dependencies (weasyprint, jinja2, pydantic)
├── uv.lock                      ← Locked dependency versions (auto-managed by uv)
│
├── scripts/
│   ├── generate.py              ← Thin CLI entrypoint: argparse + generation pipeline (~95 lines)
│   ├── encode_logo.py           ← Encodes a local image file to a base64 data URI and injects it into a payload
│   └── setup.sh                 ← Pre-syncs the Python venv (run once per session before first generation)
│
├── builders/                    ← Context builder package — one module per doc type
│   ├── __init__.py              ← DocTypeConfig dataclass + REGISTRY (single registration point)
│   ├── _shared.py               ← Shared helpers: build_line_items, build_totals, get_css_path, etc.
│   ├── purchase_order.py        ← build_po_context(): PO-specific template context
│   ├── invoice.py               ← build_invoice_context(); loads CSS from assets/invoice.css
│   └── request_for_quotation.py ← build_rfq_context(); no monetary fields
│
├── schemas/
│   ├── base.py                  ← Shared base classes and mixins (MoneyMixin, etc.)
│   ├── purchase_order.py        ← Pydantic v2 model for Purchase Orders (with @computed_field)
│   ├── invoice.py               ← Pydantic v2 model for Invoices
│   └── request_for_quotation.py ← Pydantic v2 model for RFQs (no computed fields)
│
├── utils/
│   ├── paths.py                 ← Project root path constants (ROOT, TEMPLATES_DIR, ASSETS_DIR)
│   ├── formatting.py            ← Currency formatting (USD/American: $1,234.56), date formatting
│   ├── file_naming.py           ← Auto-naming logic: <PREFIX>_YYYYMMDD_XXXX.pdf (PREFIX = PO, INV, RFQ)
│   ├── logo.py                  ← Logo resolver: validates data URI (data:image/...;base64,...); rejects file paths and URLs
│   └── preview.py               ← OS-aware PDF opener (macOS: open, Linux: xdg-open, Win: start)
│
├── templates/
│   ├── base.html                    ← Shared page layout — imports style.css, injects theme CSS variables
│   ├── purchase_order.html          ← PO Jinja2 template extending base.html
│   ├── invoice.html                 ← Invoice Jinja2 template extending base.html
│   └── request_for_quotation.html   ← RFQ Jinja2 template extending base.html
│
├── assets/
│   ├── style.css                        ← Base stylesheet built entirely on CSS custom properties
│   ├── purchase_order.css               ← PO-specific component styles (loaded by builders/purchase_order.py)
│   ├── invoice.css                      ← Invoice-specific component styles (loaded by builders/invoice.py)
│   ├── request_for_quotation.css        ← RFQ-specific component styles (loaded by builders/request_for_quotation.py)
│   └── themes/                          ← Future: named theme override files
│
├── references/
│   ├── purchase_order.md            ← SOURCE OF TRUTH for the purchase_order doc type (see below)
│   ├── invoice.md                   ← SOURCE OF TRUTH for the invoice doc type
│   ├── request_for_quotation.md     ← SOURCE OF TRUTH for the request_for_quotation doc type
│   ├── EXTENDING.md                 ← Developer guide: how to add a new document type
│   ├── NEW_DOC_TYPE.md              ← Copy-paste coding agent prompt for implementing a new doc type end-to-end
│   ├── DESIGN_SYSTEM.md             ← Visual source of truth: color palette, typography, totals block design, theming
│   └── ERRORS.md                    ← All CLI error patterns and recovery steps (validation errors + setup failures)
│
├── tests/
│   └── fixtures/
│       ├── sample_po.json                   ← Valid complete PO payload (used for local testing)
│       ├── invalid_po.json                  ← PO payload missing required fields (expected: clean error)
│       ├── sample_invoice.json              ← Valid complete Invoice payload
│       ├── sample_invoice_contractor.json   ← Invoice from an individual contractor (unpaid)
│       ├── invalid_invoice.json             ← Invoice payload missing required fields
│       ├── sample_rfq.json                  ← Valid RFQ payload (addressed, with vendor + valid_until)
│       ├── sample_rfq_broadcast.json        ← Valid RFQ payload (broadcast, no vendor, no valid_until)
│       └── invalid_rfq.json                 ← RFQ payload with validation errors (expected: clean error)
│
├── output/                      ← Generated PDFs land here (.gitignored)
│
└── docs/
    ├── PRD.md                   ← Full product requirements document
    ├── PUBLISHING.md            ← Skill publishing and team setup guide
    ├── future_features.md       ← Planned future capabilities and roadmap
    └── decisions/               ← Architecture decision records (001-006)
```

---

## Key Design Decisions

**Schema-driven, not template-driven.** Every document type has a Pydantic v2 schema that defines required/optional fields, types, and validation rules. The schema is the contract — templates are just renderers.

**No LLM in the render path.** `scripts/generate.py` is a pure deterministic function. It takes a JSON payload, validates it against a Pydantic schema, renders a Jinja2 template, and writes a PDF via WeasyPrint. No model calls, no network, no side effects.

**No logic in templates.** All computation (subtotals, tax, totals, formatting) happens in Python before the template is rendered. Jinja2 templates receive a fully-resolved context dict and only do display.

**Computed fields via Pydantic `@computed_field`.** Derived values (`subtotal`, `tax_amount`, `grand_total`, line item `total`) are always calculated from the raw inputs. They are never accepted from the payload — Pydantic validates and computes them automatically.

**File-path-only `--payload`.** Agents write the JSON to a temp file and pass the path. This avoids shell quoting issues with inline JSON and works identically across all platforms and agent runtimes.

**CSS custom properties only.** `assets/style.css` uses `--var: value` everywhere. No hardcoded colors, sizes, or fonts outside of `:root`. This makes theming a single override file.

**USD/American formatting in Phase 1.** All monetary values are formatted as `$1,234.56`. Multi-currency support is explicitly backlogged.

**Preview is best-effort.** The `--preview` flag attempts to open the PDF with the OS default viewer. If no display is available (headless CI, SSH session), it silently skips — never errors.

---

## Source-of-Truth Rule: `references/<doc_type>.md`

Before touching a schema file, a template, or a fixture for any document type — **read the corresponding `references/<doc_type>.md` first**.

Each reference file defines:

- All fields (required/optional), their types, defaults, and descriptions
- Computed fields (never ask the user for these)
- Validation rules
- The Claude data collection protocol for that doc type
- An example payload with expected computed output
- Layout notes for the template

The Pydantic model and Jinja2 template are derived from the reference. The reference is never derived from the code.

---

## How to Add a New Document Type

Five files. No other existing files change.

```text
1. Add references/<doc_type>.md    → Define all fields, rules, computed fields, layout notes
2. Add schemas/<doc_type>.py       → Pydantic v2 model derived from the reference
3. Add templates/<doc_type>.html   → Jinja2 template extending base.html
4. Add builders/<doc_type>.py      → build_<doc_type>_context() function
5. Register in builders/__init__.py → Add one DocTypeConfig entry to REGISTRY
```

That's it. `base.html`, `style.css`, and `generate.py`'s core engine are never modified when adding a doc type. See `references/EXTENDING.md` for full step-by-step guidance. For a single-session coding agent prompt, see `references/NEW_DOC_TYPE.md`.

---

## Technical Decision Records

All non-obvious technical decisions are recorded in `docs/decisions/` using the naming convention `00X-{short-description}.md`. Each file captures: the context that forced the decision, what was decided, and the consequences.

Before changing any architectural pattern or constraint in this codebase, check whether a decision record exists for it. If you're making a new architectural decision, create a record.

Current decisions:

- [001-decimal-for-money](docs/decisions/001-decimal-for-money.md) — Use `Decimal` (not `float`) for all monetary fields
- [002-python-only-formatting](docs/decisions/002-python-only-formatting.md) — All formatting in Python; templates receive strings
- [003-file-path-payload](docs/decisions/003-file-path-payload.md) — `--payload` accepts file path only, not inline JSON
- [004-argparse-only-cli](docs/decisions/004-argparse-only-cli.md) — Use stdlib `argparse`; no CLI framework dependencies
- [005-skill-marketplace-publishing](docs/decisions/005-skill-marketplace-publishing.md) — Skill marketplace publishing: GitHub-first distribution + vercel-labs/agent-skills registry (Option A); npm package documented for future (Option B)
- [006-logo-data-uri-only](docs/decisions/006-logo-data-uri-only.md) — Logo field accepts only base64 data URIs; file paths and URLs rejected at the CLI level to prevent path traversal and SSRF

---

## The `.ai/` Folder

The `.ai/` folder (gitignored) contains agent planning artifacts. AI agents working on this project should read and update these files:

| File | Purpose |
|---|---|
| `.ai/implementation-plan.md` | The current phased implementation plan. Read this before starting any work. |
| `.ai/current-plan.md` | Active work-in-progress context for the current session. |
| `.ai/memory.md` | Cross-session notes: patterns discovered, decisions made, gotchas encountered. |
| `.ai/errors.md` | Log of errors encountered and how they were resolved. Update this when you fix a non-obvious bug. |
