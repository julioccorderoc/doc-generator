# PRD: `doc-generator` — Claude Skill for Structured PDF Generation

**Status:** Implemented  
**Last updated:** 2026-04-09  
**Stack:** Python · WeasyPrint · Jinja2 · uv  

## 1. Problem Statement

Generating professional business documents (Purchase Orders, Invoices, etc.) is repetitive, error-prone when done manually, and typically requires expensive SaaS tools or fragile spreadsheet templates. The goal is to give Claude a deterministic, local, zero-cost document generation capability — where Claude handles data collection and the skill handles rendering.

## 2. Goals

- **Deterministic output:** same input → same PDF, always. No LLM involved in rendering.
- **Schema-driven:** every document type has a defined required/optional field contract.
- **Claude-native:** Claude collects and validates the data, then dispatches to the renderer.
- **Extensible:** adding a new document type = add a schema + a Jinja2 template. No changes to the core engine.
- **Local-first:** runs entirely on the user's machine. No external APIs, no paid services.

## 3. Non-Goals

- This is not a UI or web app.
- This does not store documents — it generates them on demand.
- This does not handle e-signatures, PDF forms (fillable fields), or digital delivery.

## 4. Technical Stack

| Layer | Tool | Rationale |
|---|---|---|
| PDF rendering | WeasyPrint | Free, open-source, full CSS support including flexbox |
| Templating | Jinja2 | Industry standard, supports loops/conditionals/filters |
| Schema validation | Pydantic v2 | Clean validation errors Claude can interpret and relay to the user |
| Dependency management | uv | Fast, reproducible, no virtualenv ceremony |
| Language | Python 3.11+ | — |

## 5. Project Structure

This project is developed as a standalone VS Code project that mirrors the Claude skill file structure exactly. This means local testing and skill installation use the same codebase with zero adaptation.

```text
doc-generator/
│
├── CLAUDE.md                    ← Agent entry point: CLI contract, conventions, design decisions
├── SKILL.md                     ← Claude skill definition (trigger, data collection, invocation)
├── README.md                    ← Project overview and setup instructions
│
├── pyproject.toml               ← uv project manifest with dependencies (weasyprint, jinja2, pydantic)
├── uv.lock                      ← Locked dependency versions (auto-managed by uv)
│
├── .claude/
│   └── settings.json            ← Pre-approved permissions: Write(/tmp/) + Bash CLI invocation
│
├── .github/
│   └── workflows/
│       └── ci.yml               ← pytest on every push/PR
│
├── scripts/
│   ├── generate.py              # CLI: --doc_type, --payload, --preview, --output_name, --output_dir, --save_payload
│   └── encode_logo.py           # Encodes a local image to base64 data URI for the logo field
│
├── builders/                    ← Context builder package — one module per doc type
│   ├── __init__.py              ← DocTypeConfig dataclass + REGISTRY
│   ├── _shared.py               ← Shared helpers: build_line_items, build_totals, get_css_path, etc.
│   ├── purchase_order.py
│   ├── invoice.py
│   └── request_for_quotation.py
│
├── schemas/
│   ├── base.py                  ← Shared base classes and mixins (Money type, validators)
│   ├── purchase_order.py        ← Pydantic v2 model for POs (with @computed_field)
│   ├── invoice.py               ← Pydantic v2 model for Invoices
│   └── request_for_quotation.py ← Pydantic v2 model for RFQs (no computed fields)
│
├── utils/
│   ├── paths.py                 ← Project root path constants (ROOT, TEMPLATES_DIR, ASSETS_DIR, OUTPUT_DIR)
│   ├── formatting.py            ← Currency formatting (USD/American: $1,234.56), date formatting
│   ├── file_naming.py           ← Auto-naming logic: <PREFIX>_YYYYMMDD_XXXX.pdf (PREFIX = PO, INV, RFQ)
│   ├── logo.py                  ← Logo resolver: validates base64 data URIs; rejects file paths and URLs
│   └── preview.py               ← OS-aware PDF opener (macOS: open, Linux: xdg-open, Win: start)
│
├── templates/
│   ├── base.html                ← Shared layout — imports style.css, injects theme CSS variables
│   ├── purchase_order.html
│   ├── invoice.html
│   └── request_for_quotation.html
│
├── assets/
│   ├── style.css                ← Base stylesheet built entirely on CSS custom properties
│   ├── purchase_order.css       ← PO-specific component styles
│   ├── invoice.css              ← Invoice-specific component styles
│   ├── request_for_quotation.css ← RFQ-specific component styles
│   └── themes/                  ← Future: named theme override files
│
├── references/
│   ├── purchase_order.md        ← SOURCE OF TRUTH for the purchase_order doc type
│   ├── invoice.md               ← SOURCE OF TRUTH for the invoice doc type
│   ├── request_for_quotation.md ← SOURCE OF TRUTH for the request_for_quotation doc type
│   ├── po_terms_conditions.md   ← Standard T&C preset text for PO annex
│   ├── EXTENDING.md             ← Developer guide: how to add a new document type
│   ├── NEW_DOC_TYPE.md          ← Copy-paste coding agent prompt for implementing a new doc type
│   ├── DESIGN_SYSTEM.md         ← Visual source of truth: color palette, typography, theming
│   └── ERRORS.md                ← All CLI error patterns and recovery steps
│
├── tests/
│   └── fixtures/
│       ├── sample_po.json
│       ├── sample_po_with_annex.json
│       ├── invalid_po.json
│       ├── sample_invoice.json
│       ├── sample_invoice_contractor.json
│       ├── invalid_invoice.json
│       ├── sample_rfq.json
│       ├── sample_rfq_broadcast.json
│       └── invalid_rfq.json
│
├── output/                      ← Generated PDFs land here (.gitignored)
│
└── docs/
    ├── PRD.md                   ← This file
    ├── PUBLISHING.md            ← Skill publishing and team setup guide
    ├── future_features.md       ← Planned future capabilities
    └── decisions/               ← Architecture decision records (001-006)
```

### Why this structure works as a skill

Claude skills are folders with a `SKILL.md` at the root and optional `scripts/`, `assets/`, and `references/` subdirectories. This project is already organized that way — so installing it as a Claude skill requires no restructuring, just packaging.

The `references/` folder is the key extensibility surface: when Claude encounters a doc type, it reads the corresponding `references/<doc_type>.md` to understand exactly what fields are needed, their types, validation rules, and examples. This keeps SKILL.md lean and doc-type-specific knowledge out of the main entrypoint.

## 6. How It Works (Runtime Flow)

```text
User request
     │
     ▼
Claude reads SKILL.md
     │
     ▼
Claude identifies doc_type (e.g. "purchase_order")
     │
     ▼
Claude loads schema → identifies missing fields
     │
     ▼
Claude collects data (asks user / fetches from tool / uses provided data)
     │
     ▼
Claude validates payload against Pydantic schema
     │
     ▼
Claude calls: python scripts/generate.py --doc_type purchase_order --payload /tmp/payload.json
     │
     ▼
generate.py → Jinja2 renders HTML → WeasyPrint writes PDF → <output_dir>/PO_YYYYMMDD_XXXX.pdf (absolute path printed to stdout)
     │
     ▼
Claude presents the file to the user
```

## 7. Development Phases

### Phase 1 — Purchase Order

**Objective:** Build the full stack end-to-end with the simplest real document type.

> **Note:** The PO field schema (required fields, types, computed fields, validation rules) will be defined in a dedicated prompt step before implementation begins. The output of that step will live in `references/purchase_order.md` and become the source of truth for both the Pydantic model and Claude's data collection behavior. Do not start coding Phase 1 until that reference file exists.

**Deliverables:**

- [x] `references/purchase_order.md` — field reference (produced via schema prompt, see above)
- [x] `schemas/purchase_order.py` — Pydantic model derived from the reference
- [x] `templates/base.html` — page layout, font imports, shared CSS variables, optional logo slot
- [x] `templates/purchase_order.html` — PO layout with line items table
- [x] `assets/style.css` — clean professional styling, USD/American number formatting
- [x] `scripts/generate.py` — CLI dispatcher (doc_type → schema → template → PDF), with `--preview` flag
- [x] `pyproject.toml` — uv project with weasyprint + jinja2 + pydantic
- [x] `tests/fixtures/sample_po.json` and `tests/fixtures/invalid_po.json`
- [x] Local test: `uv run python scripts/generate.py --doc_type purchase_order --payload tests/fixtures/sample_po.json --preview`

**Acceptance criteria:**

- Given a valid JSON payload, produces a clean single-page PDF
- `--preview` opens the PDF immediately after generation
- Given an invalid payload, prints a structured, human-readable validation error
- Computed totals match manual calculation
- Logo renders correctly when provided (base64 data URI); document renders cleanly without it

### Phase 2 — Invoice

**Objective:** Prove extensibility by adding a second doc type with minimal effort.

> **Same process as Phase 1:** schema is defined via a dedicated prompt step first, producing `references/invoice.md`, then the Pydantic model and template follow from it.

**Delta from PO — what's different:**

- Adds `invoice_number`, `due_date`, `payment_terms`
- Adds `bill_to` (may differ from vendor/buyer on a PO)
- Adds `paid` boolean + `amount_paid` optional field
- Balance due = `grand_total - amount_paid`
- Different layout: more emphasis on payment details block at the bottom

**Deliverables:**

- [x] `references/invoice.md` — field reference (produced via schema prompt)
- [x] `schemas/invoice.py`
- [x] `templates/invoice.html`
- [x] Updated `generate.py` to route `--doc_type invoice`
- [x] `tests/fixtures/sample_invoice.json` and `tests/fixtures/invalid_invoice.json`
- [x] Local test with `--preview`

**Acceptance criteria:**

- Existing PO generation is unaffected
- Adding the invoice required zero changes to `base.html`, `style.css`, or `generate.py`'s core engine

### Phase 3 — Extensibility Pattern & SKILL.md

**Objective:** Document and codify how to add future document types. Then write the SKILL.md so Claude knows how to operate the tool.

**Extensibility contract — adding a new doc type (five files, nothing else changes):**

```text
1. Add references/<doc_type>.md    → Field reference, quirks, minimal payload shape
2. Add schemas/<doc_type>.py       → Pydantic v2 model derived from the reference
3. Add templates/<doc_type>.html   → Jinja2 template extending base.html
4. Add builders/<doc_type>.py      → Context builder function
5. Register in builders/__init__.py → One DocTypeConfig entry added to REGISTRY
```

`generate.py`, `base.html`, and `style.css` are never modified when adding a doc type.

**SKILL.md content outline:**

- Trigger conditions (when to use this skill)
- Supported `doc_types` table with required fields per type
- Data collection protocol (how Claude should gather missing fields)
- Validation error handling (how to relay Pydantic errors back to the user)
- Invocation command template
- Output location and how to present the file

**Deliverables:**

- [x] `SKILL.md` — complete Claude operating instructions
- [x] `references/EXTENDING.md` — developer guide for adding new doc types
- [x] End-to-end test of the full Claude skill flow (local simulation)

### Phase 4 — Skill Installation & Claude Testing

**Objective:** Install as a real Claude skill and validate the full loop.

**Steps:**

1. Package the skill folder (zip or `.skill` file per Claude skill format)
2. Install via Claude skill manager
3. Run real prompts against the installed skill:
   - "Generate a purchase order for vendor Acme Corp, 50 units of X at $12 each"
   - "Create an invoice for the services we delivered last month" (Claude should ask for missing data)
4. Confirm Claude triggers the skill correctly, collects data, and produces the PDF

**Acceptance criteria:**

- Claude reads SKILL.md without being explicitly told to
- Claude identifies and asks for missing required fields before generating
- Claude does not hallucinate fields not in the schema
- PDF output is indistinguishable from Phase 1/2 local test output

## 8. Testing Strategy

### Local testing with uv

```bash
# Install deps
uv sync

# Generate a PO from a sample payload (opens preview automatically)
uv run python scripts/generate.py --doc_type purchase_order --payload tests/fixtures/sample_po.json --preview

# Generate an invoice
uv run python scripts/generate.py --doc_type invoice --payload tests/fixtures/sample_invoice.json --preview

# Test validation error handling (missing required field)
uv run python scripts/generate.py --doc_type purchase_order --payload tests/fixtures/invalid_po.json
```

### Test fixtures

Each phase ships with:

- `tests/fixtures/sample_<doc_type>.json` — valid complete payload (logo set to `null` for portability)
- `tests/fixtures/invalid_<doc_type>.json` — payload missing required fields (expected: clean error)

## 9. Resolved Design Decisions

| # | Decision | Resolution |
|---|---|---|
| 1 | Logo/branding | Optional. Root-level `logo` field on all doc types. Must be a base64 data URI. `scripts/encode_logo.py` handles encoding from a file path (keeps base64 off Claude's context). The template renders cleanly with or without it. See [006-logo-data-uri-only](decisions/006-logo-data-uri-only.md). |
| 2 | `--payload` format | File path only (e.g. `--payload tests/fixtures/sample_po.json`). Avoids shell escaping issues and maps naturally to how Claude would write a temp file before invoking the script. |
| 3 | Currency formatting | USD / American standard for Phase 1 and 2 (`$1,234.56`). Multi-currency support is backlog. |
| 4 | PDF naming | Auto-named using format `<PREFIX>_YYYYMMDD_XXXX.pdf` (e.g. `PO_20260316_0001.pdf`). PREFIX comes from `DocTypeConfig.file_prefix` (PO, INV, RFQ). Custom naming via `--output_name`. See [004-argparse-only-cli](decisions/004-argparse-only-cli.md). |
| 5 | `--preview` flag | Included from Phase 1. Opens the generated PDF immediately after creation using the OS default viewer. |
| 6 | Skill publishing | GitHub-first distribution via `npx skills add`. See [005-skill-marketplace-publishing](decisions/005-skill-marketplace-publishing.md). |
| 7 | Logo security | Logo field accepts only base64 data URIs; file paths and URLs rejected at the CLI level. See [006-logo-data-uri-only](decisions/006-logo-data-uri-only.md). |

## 10. Future Doc Types (Backlog)

- `packing_slip` — simpler than PO, no pricing, just quantities and shipping info
- `quote` / `estimate` — like an invoice but with expiry date and "not a tax invoice" watermark
- `statement_of_work` — multi-section, narrative + deliverables table
- `receipt` — minimal single-transaction document
- `credit_note` — invoice adjustment/reversal

**Future capabilities:**

- Multi-currency support (MXN, EUR, etc.) with localized number formatting
- Configurable branding profiles (logo + color palette as a named config, not per-generation)

## 11. Definition of Done (Full Project)

- [x] PO, Invoice, and RFQ generate clean, professional PDFs from a JSON payload
- [x] Validation errors are human-readable and actionable
- [x] Adding a new doc type touches exactly 5 files (see EXTENDING.md)
- [x] SKILL.md is complete and Claude triggers + uses the skill correctly without hand-holding
- [x] All local tests pass via `uv run pytest`
- [x] Skill installed and validated in live Claude environment via `npx skills add`
