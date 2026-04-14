# doc-generator

Deterministic, schema-driven PDF generator for business docs (POs, Invoices, RFQs). Invocable by **any AI agent** with shell access — Claude, Cursor, Gemini, Codex, etc. No LLM in render path. Same input → same PDF.

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

Any agent must use this interface. Complete contract — no interactive prompts, no implicit state.

```text
uv run python scripts/generate.py --doc_type <type> --payload <path> [--preview] [--save_payload]
```

| Argument | Required | Description |
|---|---|---|
| `--doc_type` | Yes | Doc type slug. Must match registered type (e.g. `purchase_order`, `invoice`, `request_for_quotation`). |
| `--payload` | Yes | Path to JSON file with doc data. **File path only** — not inline JSON. Avoids shell escaping; agents write temp file before invoking. |
| `--preview` | No | Opens generated PDF with OS default viewer. Gracefully no-ops in headless environments. |
| `--output_name` | No | Custom filename stem. Output becomes `<doc_type>_<name>.pdf`. Defaults to date + sequential counter. |
| `--output_dir` | No | Directory for generated PDF. Defaults to `<project_root>/output/`. Pass `$(pwd)` for caller's cwd. |
| `--save_payload` | No | Saves validated payload (with computed fields) as `.json` alongside PDF, same filename stem. |

**On success:** Writes PDF to target dir (default `<project_root>/output/`), prints **absolute** path to stdout. Exit `0`. Agents must use this path directly — never prepend cwd. With `--save_payload`, `.json` file also written.

**On validation error:** Prints structured error to stdout describing failed fields. Exit `1`. No PDF written.

**On unknown doc_type:** Prints registered doc types to stdout. Exit `1`.

Agents: capture stdout, check exit code.

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
│       └── ci.yml               ← Runs pytest on every push/PR (ubuntu-latest)
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

**Schema-driven, not template-driven.** Every doc type has Pydantic v2 schema defining fields, types, validation. Schema is contract — templates are renderers.

**No LLM in render path.** `scripts/generate.py` is pure deterministic. Takes JSON, validates via Pydantic, renders Jinja2, writes PDF via WeasyPrint. No model calls, no network.

**No logic in templates.** All computation (subtotals, tax, totals, formatting) in Python before render. Templates receive fully-resolved context dict, only display.

**Computed fields via Pydantic `@computed_field`.** Derived values (`subtotal`, `tax_amount`, `grand_total`, line item `total`) always calculated from raw inputs. Never accepted from payload.

**File-path-only `--payload`.** Agents write JSON to temp file and pass path. Avoids shell quoting issues, works identically across all platforms.

**CSS custom properties only.** `assets/style.css` uses `--var: value` everywhere. No hardcoded colors/sizes/fonts outside `:root`. Theming = single override file.

**USD/American formatting in Phase 1.** All money formatted as `$1,234.56`. Multi-currency backlogged.

**Preview is best-effort.** `--preview` attempts OS default viewer. No display available → silently skips, never errors.

---

## Source-of-Truth Rule: `references/<doc_type>.md`

Before touching schema, template, or fixture — **read `references/<doc_type>.md` first**.

Each reference defines:

- All fields (required/optional), types, defaults, descriptions
- Computed fields (never ask user for these)
- Validation rules
- Claude data collection protocol
- Example payload with expected computed output
- Layout notes

Pydantic model and Jinja2 template derive from reference. Reference never derives from code.

---

## How to Add a New Document Type

Five files. No existing files change.

```text
1. Add references/<doc_type>.md    → Define all fields, rules, computed fields, layout notes
2. Add schemas/<doc_type>.py       → Pydantic v2 model derived from the reference
3. Add templates/<doc_type>.html   → Jinja2 template extending base.html
4. Add builders/<doc_type>.py      → build_<doc_type>_context() function
5. Register in builders/__init__.py → Add one DocTypeConfig entry to REGISTRY
```

`base.html`, `style.css`, and `generate.py` core never modified when adding doc type. See `references/EXTENDING.md` for full guide. For single-session agent prompt, see `references/NEW_DOC_TYPE.md`.

---

## Technical Decision Records

All non-obvious decisions recorded in `docs/decisions/` as `00X-{short-description}.md`. Each captures: context, decision, consequences.

Before changing architectural patterns, check for existing record. Making new decision → create record.

- [001-decimal-for-money](docs/decisions/001-decimal-for-money.md) — `Decimal` not `float` for money
- [002-python-only-formatting](docs/decisions/002-python-only-formatting.md) — All formatting in Python; templates receive strings
- [003-file-path-payload](docs/decisions/003-file-path-payload.md) — `--payload` accepts file path only
- [004-argparse-only-cli](docs/decisions/004-argparse-only-cli.md) — stdlib `argparse`; no CLI framework deps
- [005-skill-marketplace-publishing](docs/decisions/005-skill-marketplace-publishing.md) — GitHub-first distribution + vercel-labs/agent-skills registry
- [006-logo-data-uri-only](docs/decisions/006-logo-data-uri-only.md) — Logo accepts only base64 data URIs; file paths/URLs rejected

---

## The `.ai/` Folder

`.ai/` (gitignored) contains agent planning artifacts. AI agents should read/update:

| File | Purpose |
|---|---|
| `.ai/implementation-plan.md` | Current phased plan. Read before starting work. |
| `.ai/current-plan.md` | Active WIP context for current session. |
| `.ai/memory.md` | Cross-session notes: patterns, decisions, gotchas. |
| `.ai/errors.md` | Error log + resolutions. Update when fixing non-obvious bugs. |
