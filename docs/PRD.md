# PRD: `doc-generator` — Claude Skill for Structured PDF Generation

**Status:** Draft  
**Last updated:** 2026-03-16  
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
├── SKILL.md
│
├── pyproject.toml
├── uv.lock
│
├── scripts/
│   └── generate.py              # CLI: --doc_type, --payload, --theme, --preview
│
├── schemas/
│   ├── base.py                  # Shared base classes / mixins (e.g. MoneyMixin)
│   ├── purchase_order.py        # Pydantic model w/ computed fields
│   └── invoice.py
│
├── utils/
│   ├── formatting.py            # Currency formatting, date formatting (USD/American standard), etc...
│   ├── file_naming.py           # Auto-naming logic: po_YYYYMMDD_XXXX.pdf
│   ├── logo.py                  # Logo resolver: accepts file path or URL, returns base64
│   └── preview.py               # OS-aware PDF opener (macOS: open, Linux: xdg-open, Win: start)
│
├── templates/
│   ├── base.html                # Shared layout — imports style.css, injects theme overrides
│   ├── purchase_order.html
│   └── invoice.html
│
├── assets/
│   ├── style.css                # Base stylesheet — built entirely on CSS custom properties
│   └── themes/                  # ← future: named theme overrides
│       └── .gitkeep
│
├── references/
│   ├── purchase_order.md        # Field reference: all fields, types, rules, examples
│   ├── invoice.md
│   └── EXTENDING.md
│
├── tests/
│   └── fixtures/
│       ├── sample_po.json
│       ├── invalid_po.json
│       ├── sample_invoice.json
│       └── invalid_invoice.json
│
├── output/                      # .gitignored
│
└── docs/
    └── PRD.md
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
Claude calls: python scripts/generate.py --doc_type purchase_order --payload '{...}'
     │
     ▼
generate.py → Jinja2 renders HTML → WeasyPrint writes PDF → output/po_YYYYMMDD_XXXX.pdf
     │
     ▼
Claude presents the file to the user
```

## 7. Development Phases

### Phase 1 — Purchase Order

**Objective:** Build the full stack end-to-end with the simplest real document type.

> **Note:** The PO field schema (required fields, types, computed fields, validation rules) will be defined in a dedicated prompt step before implementation begins. The output of that step will live in `references/purchase_order.md` and become the source of truth for both the Pydantic model and Claude's data collection behavior. Do not start coding Phase 1 until that reference file exists.

**Deliverables:**

- [ ] `references/purchase_order.md` — field reference (produced via schema prompt, see above)
- [ ] `schemas/purchase_order.py` — Pydantic model derived from the reference
- [ ] `templates/base.html` — page layout, font imports, shared CSS variables, optional logo slot
- [ ] `templates/purchase_order.html` — PO layout with line items table
- [ ] `assets/style.css` — clean professional styling, USD/American number formatting
- [ ] `scripts/generate.py` — CLI dispatcher (doc_type → schema → template → PDF), with `--preview` flag
- [ ] `pyproject.toml` — uv project with weasyprint + jinja2 + pydantic
- [ ] `tests/fixtures/sample_po.json` and `tests/fixtures/invalid_po.json`
- [ ] Local test: `uv run python scripts/generate.py --doc_type purchase_order --payload tests/fixtures/sample_po.json --preview`

**Acceptance criteria:**

- Given a valid JSON payload, produces a clean single-page PDF
- `--preview` opens the PDF immediately after generation
- Given an invalid payload, prints a structured, human-readable validation error
- Computed totals match manual calculation
- Logo renders correctly when provided (file path or URL); document renders cleanly without it

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

- [ ] `references/invoice.md` — field reference (produced via schema prompt)
- [ ] `schemas/invoice.py`
- [ ] `templates/invoice.html`
- [ ] Updated `generate.py` to route `--doc_type invoice`
- [ ] `tests/fixtures/sample_invoice.json` and `tests/fixtures/invalid_invoice.json`
- [ ] Local test with `--preview`

**Acceptance criteria:**

- Existing PO generation is unaffected
- Adding the invoice required zero changes to `base.html`, `style.css`, or `generate.py`'s core engine

### Phase 3 — Extensibility Pattern & SKILL.md

**Objective:** Document and codify how to add future document types. Then write the SKILL.md so Claude knows how to operate the tool.

**Extensibility contract — adding a new doc type:**

```text
1. Add schemas/<doc_type>.py     → Pydantic model
2. Add templates/<doc_type>.html → Jinja2 template extending base.html
3. Register in scripts/generate.py REGISTRY dict (one line)
4. Update SKILL.md doc_types section
```

That's it. No other files change.

**SKILL.md content outline:**

- Trigger conditions (when to use this skill)
- Supported `doc_types` table with required fields per type
- Data collection protocol (how Claude should gather missing fields)
- Validation error handling (how to relay Pydantic errors back to the user)
- Invocation command template
- Output location and how to present the file

**Deliverables:**

- [ ] `SKILL.md` — complete Claude operating instructions
- [ ] `references/EXTENDING.md` — developer guide for adding new doc types
- [ ] End-to-end test of the full Claude skill flow (local simulation)

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

- `tests/fixtures/sample_<doc_type>.json` — valid complete payload (with and without logo)
- `tests/fixtures/invalid_<doc_type>.json` — payload missing required fields (expected: clean error)

## 9. Resolved Design Decisions

| # | Decision | Resolution |
|---|---|---|
| 1 | Logo/branding | Optional. User provides a local file path or URL. Claude handles passing it to the renderer. The template renders cleanly with or without it. |
| 2 | `--payload` format | File path only (e.g. `--payload tests/fixtures/sample_po.json`). Avoids shell escaping issues and maps naturally to how Claude would write a temp file before invoking the script. |
| 3 | Currency formatting | USD / American standard for Phase 1 and 2 (`$1,234.56`). Multi-currency support is backlog. |
| 4 | PDF naming | Auto-named using format `<doc_type>_YYYYMMDD_XXXX.pdf` (e.g. `po_20260316_0001.pdf`). User can ask Claude to rename or use a custom format at any time. |
| 5 | `--preview` flag | Included from Phase 1. Opens the generated PDF immediately after creation using the OS default viewer. |

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

- [ ] PO and Invoice generate clean, professional PDFs from a JSON payload
- [ ] Validation errors are human-readable and actionable
- [ ] Adding a new doc type touches ≤ 3 files
- [ ] SKILL.md is complete and Claude triggers + uses the skill correctly without hand-holding
- [ ] All local tests pass via `uv run`
- [ ] Skill installed and validated in live Claude environment
