# Plan: Multi-Language Support

**Status:** Ready to implement — not yet started.
**Project root:** `/Users/juliocordero/Documents/NCL/doc-generator`
**Run tests:** `uv run pytest` (no system deps needed for unit tests)
**Run generate:** `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py ...`

---

## Context & Background

`doc-generator` is a schema-driven PDF generation CLI (no LLM in the render path). It
supports three document types: `purchase_order`, `invoice`, `request_for_quotation`.

**Current state (as of Phase 8):**
All three templates contain hardcoded English strings: document titles, column headers,
section labels, totals-row labels, status text, and UI phrases. There is no language
field in any schema, no translation file, and no translation lookup in any builder.

The one exception is `status_label` in `builders/invoice.py` (lines 43–45), which is
already computed in Python — making it the only label already positioned correctly for
localisation.

The `currency` field in `schemas/purchase_order.py` and `schemas/invoice.py` establishes
the pattern to follow: a string field with a default, validated against a frozenset of
supported values defined in Python. Language support follows the same pattern.

**Goal:** Allow any payload to specify `"language": "fr"` (or `"de"`, `"es"`, etc.) and
produce a fully localised PDF — translated document title, column headers, section labels,
and status text. English (`"en"`) is the default; omitting `"language"` from any payload
produces output identical to today's. No existing tests break.

**Design rules that must be preserved:**
- `docs/decisions/002-python-only-formatting.md` — templates receive only strings. Labels
  are resolved in Python builders; templates never see language codes or conditional logic.
- `references/EXTENDING.md §3.3` — only `{% if %}`, `{% for %}`, and `{{ value }}` in
  templates. No filters beyond `nl2br`. No arithmetic, no string operations.

---

## Supported Languages

| Code | Name       | Native Name | v1 Status |
|------|------------|-------------|-----------|
| en   | English    | English     | ✅ default |
| es   | Spanish    | Español     | ✅         |
| fr   | French     | Français    | ✅         |
| de   | German     | Deutsch     | ✅         |
| zh   | Chinese    | 中文         | ✅         |
| pt   | Portuguese | Português   | ✅         |

**Selection rationale:**
- **en** — Global business lingua franca. Current default.
- **es** — Second-most-used language in international B2B; covers Latin America and Spain.
- **fr** — Official language of 29 countries; major EU trade language; widely used in
  Francophone Africa B2B.
- **de** — Largest EU economy; dominant in manufacturing and industrial procurement.
- **zh** — World's largest goods exporter; essential for Asia-Pacific supply chains.
- **pt** — Brazil (9th largest economy) plus Lusophone Africa.

**RTL consideration:** Arabic (`ar`) and Hebrew (`he`) require `dir="rtl"` on the `<html>`
element and CSS layout changes (`text-align`, flex-direction reversal on address blocks
and totals). WeasyPrint supports bidi text natively, but template and CSS changes make
this non-trivial. **RTL is out of scope for v1.** It should be added as a dedicated phase
once the LTR translation infrastructure is in place. A v2 note is recorded below in
Key Invariants.

---

## Architecture Reference

### Where labels currently live

| Location | Type | Labels |
|---|---|---|
| `templates/purchase_order.html` | Hardcoded HTML | `"Purchase Order"`, `"Vendor"`, `"Buyer"`, `"Delivery Date"`, `"Payment Terms"`, `"Shipping Method"`, `"#"`, `"SKU"`, `"Description"`, `"Unit"`, `"Qty"`, `"Unit Price"`, `"Total"`, `"Notes"`, `"Total Units"`, `"Subtotal"`, `"Tax (...)"`, `"Shipping"`, `"Grand Total"`, `"Terms & Conditions"`, T&C footer sentence |
| `templates/invoice.html` | Hardcoded HTML | `"Invoice"`, `"From"`, `"Bill To"`, `"Due Date"`, `"Payment Terms"`, same line-item columns as PO, `"Notes"`, same totals as PO, `"Amount Paid"`, `"Balance Due"`, `"Payment Details"` |
| `templates/request_for_quotation.html` | Hardcoded HTML | `"Request for Quotation"`, `"Valid Until"`, `"From"`, `"To"`, `"Product"`, `"Specification"`, `"Details"`, `"Notes"`, `"Annexes & Attachments"`, `"Questions? Please contact:"` |
| `builders/invoice.py:43–45` | Python string literals | `"Paid"`, `"Partially Paid"` (already in Python — just needs to use translated label) |
| `templates/base.html:2` | Hardcoded HTML attribute | `lang="en"` |

### How language flows after this plan (payload → PDF)

**Before:**
```
JSON payload
  └─ (no language field)
         │
  Pydantic model (no language field)
         │
  builder — hardcoded EN strings in template
         │
  Jinja2 template
  └─ <div class="doc-header__type">Purchase Order</div>  ← always EN
```

**After:**
```
JSON payload
  └─ "language": "fr"   ← optional; defaults to "en"
         │
  Pydantic model
  └─ doc.language = "fr"  ← validated against SUPPORTED_LANGUAGES
         │
  builder
  └─ labels = get_labels("fr", "purchase_order")
  └─ labels["doc_title"] = "Bon de Commande"
  └─ labels["label_vendor"] = "Fournisseur"
  └─ tax_label = "Taxe (10.0%)"   ← combined in Python, never in template
         │
  template context
  └─ "labels": {"doc_title": "Bon de Commande", ...}
  └─ "tax_label": "Taxe (10.0%)"
  └─ "html_lang": "fr"
         │
  Jinja2 template
  └─ <html lang="{{ html_lang }}">
  └─ <div class="doc-header__type">{{ labels.doc_title }}</div>
```

### Config file fit in the builder pipeline

`utils/translations.py` is loaded at import time (like `_TERMS_PRESET` in
`builders/purchase_order.py`). It reads `config/languages.yml` once, builds
`SUPPORTED_LANGUAGES: frozenset[str]`, and exposes `get_labels(language, doc_type) -> dict`.

Each builder calls `get_labels(doc.language, "<doc_type>")` at the top of its context
function and passes the flat label dict as `"labels"` in the returned context. Templates
use `{{ labels.key }}` — pure variable output, no logic.

---

## Config File Design

### Format: YAML

**Chosen over JSON** because YAML supports inline comments (useful for noting
translation nuances and context for translators), has cleaner syntax for deeply nested
string maps, and is the de-facto standard for human-editable config in Python projects.

**Chosen over TOML** because YAML's multi-value inline tables (`{en: "...", fr: "..."}`
per label key) are more compact than TOML's requirement for a separate `[section.key]`
block per label.

**Dependency:** `pyyaml` must be added to `pyproject.toml`. It is a single pure-Python
package with no system dependencies and no conflict risk with the existing stack.

**No-dep alternative:** If `pyyaml` is undesirable, use TOML with Python's stdlib
`tomllib` (available since Python 3.11, which this project already requires). The
structure maps directly; only the file extension and `tomllib.loads()` call change.

### Proposed file: `config/languages.yml`

```yaml
# doc-generator translation config
# To add a language: add a code under "languages", then add the code
# as a key under every label in "labels". Claude edits this file directly.
# To fix a translation: find the label key, update the language sub-key.

languages:
  en: {name: "English",    native_name: "English"}
  es: {name: "Spanish",    native_name: "Español"}
  fr: {name: "French",     native_name: "Français"}
  de: {name: "German",     native_name: "Deutsch"}
  zh: {name: "Chinese",    native_name: "中文"}
  pt: {name: "Portuguese", native_name: "Português"}

labels:

  # ── Shared (used by purchase_order and invoice) ──────────────────────────
  shared:
    col_num:
      en: "#"
      es: "#"
      fr: "#"
      de: "#"
      zh: "#"
      pt: "#"
    col_sku:
      en: "SKU"
      es: "SKU"
      fr: "Réf."
      de: "Art.-Nr."
      zh: "货号"
      pt: "Ref."
    col_description:
      en: "Description"
      es: "Descripción"
      fr: "Description"
      de: "Beschreibung"
      zh: "描述"
      pt: "Descrição"
    col_unit:
      en: "Unit"
      es: "Unidad"
      fr: "Unité"
      de: "Einheit"
      zh: "单位"
      pt: "Unidade"
    col_qty:
      en: "Qty"
      es: "Cant."
      fr: "Qté"
      de: "Menge"
      zh: "数量"
      pt: "Qtd."
    col_unit_price:
      en: "Unit Price"
      es: "Precio Unitario"
      fr: "Prix Unitaire"
      de: "Einzelpreis"
      zh: "单价"
      pt: "Preço Unitário"
    col_total:
      en: "Total"
      es: "Total"
      fr: "Total"
      de: "Gesamt"
      zh: "合计"
      pt: "Total"
    label_notes:
      en: "Notes"
      es: "Notas"
      fr: "Notes"
      de: "Hinweise"
      zh: "备注"
      pt: "Notas"
    label_total_units:
      en: "Total Units"
      es: "Total de Unidades"
      fr: "Total Unités"
      de: "Gesamteinheiten"
      zh: "总数量"
      pt: "Total de Unidades"
    label_subtotal:
      en: "Subtotal"
      es: "Subtotal"
      fr: "Sous-total"
      de: "Zwischensumme"
      zh: "小计"
      pt: "Subtotal"
    label_tax:
      en: "Tax"
      es: "Impuesto"
      fr: "Taxe"
      de: "MwSt."
      zh: "税"
      pt: "Imposto"
    label_shipping:
      en: "Shipping"
      es: "Envío"
      fr: "Expédition"
      de: "Versand"
      zh: "运费"
      pt: "Envio"
    label_grand_total:
      en: "Grand Total"
      es: "Total General"
      fr: "Total Général"
      de: "Gesamtbetrag"
      zh: "总计"
      pt: "Total Geral"
    label_payment_terms:
      en: "Payment Terms"
      es: "Términos de Pago"
      fr: "Conditions de Paiement"
      de: "Zahlungsbedingungen"
      zh: "付款条件"
      pt: "Condições de Pagamento"

  # ── Purchase Order ────────────────────────────────────────────────────────
  purchase_order:
    doc_title:
      en: "Purchase Order"
      es: "Orden de Compra"
      fr: "Bon de Commande"
      de: "Bestellung"
      zh: "采购订单"
      pt: "Ordem de Compra"
    label_vendor:
      en: "Vendor"
      es: "Proveedor"
      fr: "Fournisseur"
      de: "Lieferant"
      zh: "供应商"
      pt: "Fornecedor"
    label_buyer:
      en: "Buyer"
      es: "Comprador"
      fr: "Acheteur"
      de: "Käufer"
      zh: "买方"
      pt: "Comprador"
    label_delivery_date:
      en: "Delivery Date"
      es: "Fecha de Entrega"
      fr: "Date de Livraison"
      de: "Lieferdatum"
      zh: "交货日期"
      pt: "Data de Entrega"
    label_shipping_method:
      en: "Shipping Method"
      es: "Método de Envío"
      fr: "Mode d'Expédition"
      de: "Versandart"
      zh: "运输方式"
      pt: "Método de Envio"
    label_terms_heading:
      en: "Terms & Conditions"
      es: "Términos y Condiciones"
      fr: "Termes et Conditions"
      de: "Geschäftsbedingungen"
      zh: "条款与条件"
      pt: "Termos e Condições"
    label_terms_footer:
      en: "These Terms are effective as of the date of the Purchase Order to which they are attached or referenced."
      es: "Estos Términos son efectivos a partir de la fecha de la Orden de Compra a la que están adjuntos o referenciados."
      fr: "Ces Termes prennent effet à la date du Bon de Commande auquel ils sont joints ou référencés."
      de: "Diese Bedingungen gelten ab dem Datum der Bestellung, der sie beigefügt oder auf die sie verwiesen werden."
      zh: "本条款自其所附或所引用的采购订单日期起生效。"
      pt: "Estes Termos entram em vigor na data da Ordem de Compra à qual estão anexados ou referenciados."

  # ── Invoice ───────────────────────────────────────────────────────────────
  invoice:
    doc_title:
      en: "Invoice"
      es: "Factura"
      fr: "Facture"
      de: "Rechnung"
      zh: "发票"
      pt: "Fatura"
    label_from:
      en: "From"
      es: "De"
      fr: "De"
      de: "Von"
      zh: "发件方"
      pt: "De"
    label_bill_to:
      en: "Bill To"
      es: "Facturar a"
      fr: "Facturer à"
      de: "Rechnungsempfänger"
      zh: "账单致"
      pt: "Cobrar a"
    label_due_date:
      en: "Due Date"
      es: "Fecha de Vencimiento"
      fr: "Date d'Échéance"
      de: "Fälligkeitsdatum"
      zh: "到期日"
      pt: "Data de Vencimento"
    label_amount_paid:
      en: "Amount Paid"
      es: "Monto Pagado"
      fr: "Montant Payé"
      de: "Gezahlter Betrag"
      zh: "已付金额"
      pt: "Valor Pago"
    label_balance_due:
      en: "Balance Due"
      es: "Saldo Pendiente"
      fr: "Solde Dû"
      de: "Ausstehender Betrag"
      zh: "应付余额"
      pt: "Saldo Devedor"
    label_payment_details:
      en: "Payment Details"
      es: "Detalles de Pago"
      fr: "Détails de Paiement"
      de: "Zahlungsdetails"
      zh: "付款详情"
      pt: "Detalhes de Pagamento"
    status_paid:
      en: "Paid"
      es: "Pagado"
      fr: "Payé"
      de: "Bezahlt"
      zh: "已付"
      pt: "Pago"
    status_partial:
      en: "Partially Paid"
      es: "Parcialmente Pagado"
      fr: "Partiellement Payé"
      de: "Teilweise Bezahlt"
      zh: "部分付款"
      pt: "Parcialmente Pago"

  # ── Request for Quotation ─────────────────────────────────────────────────
  request_for_quotation:
    doc_title:
      en: "Request for Quotation"
      es: "Solicitud de Cotización"
      fr: "Demande de Devis"
      de: "Angebotsanfrage"
      zh: "询价单"
      pt: "Pedido de Cotação"
    label_valid_until:
      en: "Valid Until"
      es: "Válido Hasta"
      fr: "Valable Jusqu'au"
      de: "Gültig bis"
      zh: "有效期至"
      pt: "Válido Até"
    label_from:
      en: "From"
      es: "De"
      fr: "De"
      de: "Von"
      zh: "发件方"
      pt: "De"
    label_to:
      en: "To"
      es: "Para"
      fr: "À"
      de: "An"
      zh: "致"
      pt: "Para"
    col_product:
      en: "Product"
      es: "Producto"
      fr: "Produit"
      de: "Produkt"
      zh: "产品"
      pt: "Produto"
    col_specification:
      en: "Specification"
      es: "Especificación"
      fr: "Spécification"
      de: "Spezifikation"
      zh: "规格"
      pt: "Especificação"
    col_details:
      en: "Details"
      es: "Detalles"
      fr: "Détails"
      de: "Details"
      zh: "详情"
      pt: "Detalhes"
    label_annexes:
      en: "Annexes & Attachments"
      es: "Anexos y Adjuntos"
      fr: "Annexes et Pièces Jointes"
      de: "Anhänge und Beilagen"
      zh: "附件与文档"
      pt: "Anexos e Documentos"
    label_contact:
      en: "Questions? Please contact:"
      es: "¿Preguntas? Comuníquese con:"
      fr: "Questions ? Veuillez contacter :"
      de: "Fragen? Bitte wenden Sie sich an:"
      zh: "如有问题，请联系："
      pt: "Dúvidas? Entre em contato com:"
```

**How Claude updates this file:** To add a language, append the code to `languages:` and
add a matching key under every label. To fix a translation, `Read` the file, locate the
label key + language sub-key, `Edit` that single line, done. No Python changes required.

---

## Implementation Steps

### Step 1 — `config/languages.yml` (new file)

Create the file at project root `config/languages.yml` with the complete YAML shown in
the Config File Design section above.

---

### Step 2 — `utils/translations.py` (new file)

Create `utils/translations.py`. This module is the single access point for translation
data. It reads the YAML once at import time (module-level, same pattern as `_TERMS_PRESET`
in `builders/purchase_order.py`).

```python
"""Translation loader for doc-generator.

Reads config/languages.yml once at import time and exposes:
  - SUPPORTED_LANGUAGES: frozenset of valid language codes
  - get_labels(language, doc_type): flat label dict ready for template context
"""
from __future__ import annotations

from pathlib import Path
import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "languages.yml"
_CONFIG: dict = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))

SUPPORTED_LANGUAGES: frozenset[str] = frozenset(_CONFIG["languages"].keys())


def get_labels(language: str, doc_type: str) -> dict[str, str]:
    """Return a flat label dict merging shared + doc-type-specific labels.

    Falls back to "en" for any key not found in the requested language.
    The returned dict is passed directly into the Jinja2 context as "labels".
    """
    lang = language if language in SUPPORTED_LANGUAGES else "en"
    labels: dict[str, str] = {}

    for key, translations in _CONFIG["labels"]["shared"].items():
        labels[key] = translations.get(lang) or translations["en"]

    if doc_type in _CONFIG["labels"]:
        for key, translations in _CONFIG["labels"][doc_type].items():
            labels[key] = translations.get(lang) or translations["en"]

    return labels
```

---

### Step 3 — `pyproject.toml`

Add `pyyaml` to the runtime dependencies:

```toml
dependencies = [
    "weasyprint>=62.0",
    "jinja2>=3.1",
    "pydantic>=2.0",
    "pyyaml>=6.0",        # ← add this line
]
```

Run `uv sync` after this change.

---

### Step 4 — `schemas/purchase_order.py`

Add the `language` field and validator to `PurchaseOrder`. The import and validator
follow the exact same pattern as `currency` + `SUPPORTED_CURRENCIES` in the multi-currency
plan.

```python
# New import (add to existing imports block):
from utils.translations import SUPPORTED_LANGUAGES

# In PurchaseOrder class, add after the `currency` field:
language: str = "en"

# Add a new field validator (after the existing tax_rate/shipping validators):
@field_validator("language", mode="after")
@classmethod
def language_supported(cls, v: str) -> str:
    if v not in SUPPORTED_LANGUAGES:
        raise ValueError(f"must be one of {sorted(SUPPORTED_LANGUAGES)}")
    return v
```

---

### Step 5 — `schemas/invoice.py`

Identical change to Step 4: import `SUPPORTED_LANGUAGES` from `utils.translations`,
add `language: str = "en"` field, add `language_supported` validator.

---

### Step 6 — `schemas/request_for_quotation.py`

Identical change to Steps 4–5: same import, field, and validator on `RequestForQuotation`.

---

### Step 7 — `builders/purchase_order.py`

Add `get_labels` import and inject labels into the context. Also compute `tax_label`
(the combined "Tax (rate%)" string) in Python so the template never does string composition.

```python
# New import (add to existing imports):
from utils.translations import get_labels

def build_po_context(doc: PurchaseOrder) -> dict:
    """Build the full Jinja2 template context for a Purchase Order."""
    labels = get_labels(doc.language, "purchase_order")   # ← add at top
    logo_data = resolve_logo(doc.buyer.logo)
    totals = build_totals(doc)                            # ← extract into variable

    return {
        # ── Header ────────────────────────────────────────────────────────
        "po_number": doc.po_number,
        "issue_date": format_date(doc.issue_date),
        "delivery_date": format_date(doc.delivery_date) if doc.delivery_date else None,

        # ── Parties ───────────────────────────────────────────────────────
        "buyer": { ... },   # unchanged
        "vendor": { ... },  # unchanged

        # ── Meta band ─────────────────────────────────────────────────────
        "payment_terms": doc.payment_terms,
        "shipping_method": doc.shipping_method,

        # ── Line items ────────────────────────────────────────────────────
        "line_items": build_line_items(doc),
        **build_line_items_meta(doc),

        # ── Totals ────────────────────────────────────────────────────────
        **totals,
        "tax_label": f"{labels['label_tax']} ({totals['tax_rate_pct']})",  # ← add

        # ── Notes / Footer / T&C ──────────────────────────────────────────
        "notes": doc.notes,
        "footer_text": build_footer_text(doc.buyer),
        "terms_sections": ( ... ),  # unchanged

        # ── Labels + HTML lang ────────────────────────────────────────────
        "labels": labels,           # ← add
        "html_lang": doc.language,  # ← add

        # ── Template infrastructure ───────────────────────────────────────
        "css_path": get_css_path(),
        "theme_css": Markup(_PO_CSS + (primary_color_css(doc.primary_color) or "")),
    }
```

---

### Step 8 — `builders/invoice.py`

Add `get_labels`, inject labels + `html_lang`, translate `status_label`, and compute
`tax_label`. The `status_label` change is the only place Python already held a label —
it now uses the config value instead of a string literal.

```python
# New import:
from utils.translations import get_labels

def build_invoice_context(doc: Invoice) -> dict:
    """Build the full Jinja2 template context for an Invoice."""
    labels = get_labels(doc.language, "invoice")   # ← add at top
    logo_data = resolve_logo(doc.issuer.logo)

    # Derive payment status — now uses translated labels from config
    if doc.paid:
        document_status = "paid"
        status_label = labels["status_paid"]           # ← was "Paid"
    elif doc.amount_paid > 0:
        document_status = "partial"
        status_label = labels["status_partial"]        # ← was "Partially Paid"
    else:
        document_status, status_label = None, None

    totals = build_totals(doc)                         # ← extract into variable

    return {
        # ── Header ────────────────────────────────────────────────────────
        "invoice_number": doc.invoice_number,
        "issue_date": format_date(doc.issue_date),
        "due_date": format_date(doc.due_date) if doc.due_date else None,
        "document_status": document_status,
        "status_label": status_label,

        # ── Parties ───────────────────────────────────────────────────────
        "issuer": { ... },   # unchanged
        "bill_to": { ... },  # unchanged

        # ── Meta band ─────────────────────────────────────────────────────
        "payment_terms": doc.payment_terms,

        # ── Line items ────────────────────────────────────────────────────
        "line_items": build_line_items(doc),
        **build_line_items_meta(doc),

        # ── Totals ────────────────────────────────────────────────────────
        **totals,
        "tax_label": f"{labels['label_tax']} ({totals['tax_rate_pct']})",  # ← add
        "amount_paid": format_currency(doc.amount_paid, doc.currency),
        "balance_due": format_currency(doc.balance_due, doc.currency),
        "show_amount_paid": doc.amount_paid > 0,

        # ── Payment details / Notes / Footer ──────────────────────────────
        "payment_details": [ ... ],  # unchanged
        "notes": doc.notes,
        "footer_text": build_footer_text(doc.issuer),

        # ── Labels + HTML lang ────────────────────────────────────────────
        "labels": labels,           # ← add
        "html_lang": doc.language,  # ← add

        # ── Template infrastructure ───────────────────────────────────────
        "css_path": get_css_path(),
        "theme_css": Markup(primary_color_css(doc.primary_color) + _INVOICE_CSS),
    }
```

---

### Step 9 — `builders/request_for_quotation.py`

Add `get_labels`, inject `labels` and `html_lang`. No status labels to translate.

```python
# New import:
from utils.translations import get_labels

def build_rfq_context(doc: RequestForQuotation) -> dict:
    """Build the full Jinja2 template context for a Request for Quotation."""
    labels = get_labels(doc.language, "request_for_quotation")  # ← add at top
    logo_data = resolve_logo(doc.logo)

    # ... all existing logic unchanged ...

    return {
        # all existing keys unchanged ...

        # ── Labels + HTML lang ────────────────────────────────────────────
        "labels": labels,           # ← add
        "html_lang": doc.language,  # ← add

        # ── Template infrastructure ───────────────────────────────────────
        "css_path": get_css_path(),
        "theme_css": Markup(theme_css),
    }
```

---

### Step 10 — `templates/base.html`

One-line change: make the `lang` attribute dynamic.

```html
<!-- Before -->
<html lang="en">

<!-- After -->
<html lang="{{ html_lang | default('en') }}">
```

The `| default('en')` guard ensures the template renders correctly even if `html_lang`
is accidentally absent from the context (defensive only; all builders set it).

---

### Step 11 — `templates/purchase_order.html`

Replace all 20 hardcoded English strings with label lookups. Full substitution map:

| Template location | Before | After |
|---|---|---|
| `doc-header__type` div | `Purchase Order` | `{{ labels.doc_title }}` |
| Vendor address label | `Vendor` | `{{ labels.label_vendor }}` |
| Buyer address label | `Buyer` | `{{ labels.label_buyer }}` |
| Meta band: delivery | `Delivery Date` | `{{ labels.label_delivery_date }}` |
| Meta band: terms | `Payment Terms` | `{{ labels.label_payment_terms }}` |
| Meta band: shipping method | `Shipping Method` | `{{ labels.label_shipping_method }}` |
| Line items `<th>` #1 | `#` | `{{ labels.col_num }}` |
| Line items `<th>` SKU | `SKU` | `{{ labels.col_sku }}` |
| Line items `<th>` desc | `Description` | `{{ labels.col_description }}` |
| Line items `<th>` unit | `Unit` | `{{ labels.col_unit }}` |
| Line items `<th>` qty | `Qty` | `{{ labels.col_qty }}` |
| Line items `<th>` price | `Unit Price` | `{{ labels.col_unit_price }}` |
| Line items `<th>` total | `Total` | `{{ labels.col_total }}` |
| Notes label | `Notes` | `{{ labels.label_notes }}` |
| Totals: Total Units row | `Total Units` | `{{ labels.label_total_units }}` |
| Totals: Subtotal row | `Subtotal` | `{{ labels.label_subtotal }}` |
| Totals: Tax row | `Tax ({{ tax_rate_pct }})` | `{{ tax_label }}` |
| Totals: Shipping row | `Shipping` | `{{ labels.label_shipping }}` |
| Totals: Grand Total row | `Grand Total` | `{{ labels.label_grand_total }}` |
| T&C annex `<h2>` | `Terms &amp; Conditions` | `{{ labels.label_terms_heading }}` |
| T&C annex footer `<p>` | `These Terms are effective...` | `{{ labels.label_terms_footer }}` |

**Note on `tax_label`:** The current template has
`<td>Tax ({{ tax_rate_pct }})</td>`. This is replaced with `<td>{{ tax_label }}</td>`
where `tax_label` is built in the Python builder (Step 7) as
`f"{labels['label_tax']} ({totals['tax_rate_pct']})"`. This preserves decision 002 —
no string composition in templates.

**Note on `&amp;`:** The YAML stores `Terms & Conditions` as plain text. With
`autoescape=True` in the Jinja2 environment (confirmed in `scripts/generate.py:40`),
`{{ labels.label_terms_heading }}` auto-escapes `&` to `&amp;` in the HTML output.
The hardcoded `&amp;` in the current template is replaced with the plain-text variable.

---

### Step 12 — `templates/invoice.html`

Replace all 18 hardcoded English strings. Map:

| Template location | Before | After |
|---|---|---|
| `doc-header__type` div | `Invoice` | `{{ labels.doc_title }}` |
| From address label | `From` | `{{ labels.label_from }}` |
| Bill To address label | `Bill To` | `{{ labels.label_bill_to }}` |
| Meta band: due date | `Due Date` | `{{ labels.label_due_date }}` |
| Meta band: terms | `Payment Terms` | `{{ labels.label_payment_terms }}` |
| All 7 line-item `<th>` | same as PO | same as PO (Step 11 map) |
| Notes label | `Notes` | `{{ labels.label_notes }}` |
| Totals: Total Units row | `Total Units` | `{{ labels.label_total_units }}` |
| Totals: Subtotal row | `Subtotal` | `{{ labels.label_subtotal }}` |
| Totals: Tax row | `Tax ({{ tax_rate_pct }})` | `{{ tax_label }}` |
| Totals: Shipping row | `Shipping` | `{{ labels.label_shipping }}` |
| Totals: Grand Total row | `Grand Total` | `{{ labels.label_grand_total }}` |
| Totals: Amount Paid row | `Amount Paid` | `{{ labels.label_amount_paid }}` |
| Totals: Balance Due row | `Balance Due` | `{{ labels.label_balance_due }}` |
| Payment details title | `Payment Details` | `{{ labels.label_payment_details }}` |

---

### Step 13 — `templates/request_for_quotation.html`

Replace all 10 hardcoded English strings. Map:

| Template location | Before | After |
|---|---|---|
| `doc-header__type` div | `Request for Quotation` | `{{ labels.doc_title }}` |
| Meta band: valid until | `Valid Until` | `{{ labels.label_valid_until }}` |
| From address label | `From` | `{{ labels.label_from }}` |
| To address label | `To` | `{{ labels.label_to }}` |
| Product summary `<th>` | `Product` | `{{ labels.col_product }}` |
| Spec table `<th>` #1 | `Specification` | `{{ labels.col_specification }}` |
| Spec table `<th>` #2 | `Details` | `{{ labels.col_details }}` |
| Notes label | `Notes` | `{{ labels.label_notes }}` |
| Annexes section label | `Annexes &amp; Attachments` | `{{ labels.label_annexes }}` |
| Contact block phrase | `Questions? Please contact:` | `{{ labels.label_contact }}` |

---

### Step 14 — Tests (`tests/test_translations.py`, new file)

Create a new test file covering the translation utilities and schema validation:

```python
import pytest
from pydantic import ValidationError

from utils.translations import SUPPORTED_LANGUAGES, get_labels
from schemas.purchase_order import PurchaseOrder
from schemas.invoice import Invoice
from schemas.request_for_quotation import RequestForQuotation


# ── SUPPORTED_LANGUAGES ───────────────────────────────────────────────────

def test_supported_languages_contains_defaults():
    assert "en" in SUPPORTED_LANGUAGES
    assert "es" in SUPPORTED_LANGUAGES
    assert "fr" in SUPPORTED_LANGUAGES
    assert "de" in SUPPORTED_LANGUAGES
    assert "zh" in SUPPORTED_LANGUAGES
    assert "pt" in SUPPORTED_LANGUAGES


# ── get_labels ────────────────────────────────────────────────────────────

def test_get_labels_en_returns_english():
    labels = get_labels("en", "purchase_order")
    assert labels["doc_title"] == "Purchase Order"
    assert labels["label_vendor"] == "Vendor"
    assert labels["label_grand_total"] == "Grand Total"


def test_get_labels_es_purchase_order():
    labels = get_labels("es", "purchase_order")
    assert labels["doc_title"] == "Orden de Compra"
    assert labels["label_vendor"] == "Proveedor"
    assert labels["label_grand_total"] == "Total General"


def test_get_labels_fr_invoice():
    labels = get_labels("fr", "invoice")
    assert labels["doc_title"] == "Facture"
    assert labels["label_bill_to"] == "Facturer à"
    assert labels["status_paid"] == "Payé"


def test_get_labels_unknown_language_falls_back_to_en():
    labels = get_labels("xx", "purchase_order")
    assert labels["doc_title"] == "Purchase Order"


def test_get_labels_shared_keys_present_for_all_doc_types():
    for doc_type in ("purchase_order", "invoice", "request_for_quotation"):
        labels = get_labels("en", doc_type)
        assert "col_description" in labels
        assert "label_notes" in labels
        assert "label_grand_total" in labels or doc_type == "request_for_quotation"


# ── Schema validation ─────────────────────────────────────────────────────

def test_po_default_language_is_en(sample_po_data):
    doc = PurchaseOrder(**sample_po_data)
    assert doc.language == "en"


def test_po_valid_language_fr(sample_po_data):
    sample_po_data["language"] = "fr"
    doc = PurchaseOrder(**sample_po_data)
    assert doc.language == "fr"


def test_po_invalid_language_raises(sample_po_data):
    sample_po_data["language"] = "xx"
    with pytest.raises(ValidationError, match="must be one of"):
        PurchaseOrder(**sample_po_data)


def test_invoice_valid_language_de(sample_invoice_data):
    sample_invoice_data["language"] = "de"
    doc = Invoice(**sample_invoice_data)
    assert doc.language == "de"


def test_rfq_valid_language_zh(sample_rfq_data):
    sample_rfq_data["language"] = "zh"
    doc = RequestForQuotation(**sample_rfq_data)
    assert doc.language == "zh"
```

Fixtures (`sample_po_data`, `sample_invoice_data`, `sample_rfq_data`) should be added to
`tests/conftest.py` (or defined locally) by loading the corresponding `tests/fixtures/`
JSON files — same pattern used in the existing `tests/test_schemas.py`.

---

## Files NOT Changed

- `scripts/generate.py` — no changes; language validation happens in the schema
- `builders/_shared.py` — `build_line_items()`, `build_totals()`, `build_footer_text()`
  are unaffected; labels are injected by the doc-type builders, not the shared helpers
- `builders/__init__.py` — REGISTRY is unchanged; no new doc types
- `assets/*.css` — no text content; CSS variables are language-agnostic
- `tests/fixtures/*.json` — existing fixtures omit `"language"`, which defaults to `"en"`;
  no changes needed; all existing tests continue to pass unchanged
- `docs/decisions/002-python-only-formatting.md` — this plan is consistent with ADR-002;
  no amendment needed
- `schemas/base.py` — `SUPPORTED_LANGUAGES` for language lives in `utils/translations.py`
  (not base.py) because it is loaded from the config file, not a hardcoded frozenset

---

## Verification

```bash
# Install new dependency
uv sync

# Full test suite (must stay green, including existing tests)
uv run pytest

# ── English (default) — must be identical to current output ───────────────
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload tests/fixtures/sample_po.json --preview
# Expected: PDF in English, visually identical to pre-plan output

# ── French PO ─────────────────────────────────────────────────────────────
# Add "language": "fr" to a copy of sample_po.json, then:
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload /tmp/po_fr.json --preview
# Expected: "Bon de Commande", "Fournisseur", "Acheteur", "Sous-total",
#           "Total Général", column headers in French

# ── German Invoice ────────────────────────────────────────────────────────
# Add "language": "de" to a copy of sample_invoice.json
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type invoice --payload /tmp/invoice_de.json --preview
# Expected: "Rechnung", "Von", "Rechnungsempfänger", "Bezahlt"/"Teilweise Bezahlt"

# ── Chinese RFQ ───────────────────────────────────────────────────────────
# Add "language": "zh" to a copy of sample_rfq.json
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type request_for_quotation --payload /tmp/rfq_zh.json --preview
# Expected: "询价单", "供应商", "规格", "附件与文档"

# ── Invalid language — clean validation error ─────────────────────────────
# Add "language": "it" to any fixture, then run:
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order --payload /tmp/po_bad_lang.json
# Expected:
#   Validation failed:
#     language: must be one of ['de', 'en', 'es', 'fr', 'pt', 'zh']
#   Exit code: 1, no PDF written

# ── Adding a new language (agent workflow) ────────────────────────────────
# Claude reads config/languages.yml, appends "it" under languages:,
# then appends an "it" key under every label in labels:, then
# adds "language": "it" to a fixture and re-runs the generate command.
# No Python changes required.
```

---

## Key Invariants to Preserve

- **English default** — omitting `"language"` from any payload produces output identical
  to today's. `language: str = "en"` in all schemas; `get_labels("en", ...)` returns the
  same strings currently hardcoded in the templates.
- **No logic in templates** (ADR-002) — templates use `{{ labels.key }}` for pure output.
  No conditionals, filters, or string operations on label values. The `tax_label`
  composed string is built in Python (Steps 7–8), not in the template.
- **No raw Decimal or date objects in context** — label injection does not touch monetary
  or date fields; ADR-002 is unaffected.
- **Existing tests pass unchanged** — `tests/fixtures/*.json` have no `"language"` key,
  which defaults to `"en"`; all schema, builder, utils, and integration tests are green.
- **Config is the only edit path for translations** — adding a language or fixing a
  translation requires only editing `config/languages.yml`. No Python code changes.
  Claude can do this in a single `Edit` call.
- **`SUPPORTED_LANGUAGES` is derived from config, not hardcoded** — the YAML
  `languages:` keys are the single source of truth; `utils/translations.py` builds
  the frozenset at import time. Adding a language to the YAML automatically makes it
  valid in all three schemas.
- **v2 RTL note** — Arabic (`ar`) and Hebrew (`he`) require `<html dir="rtl">` and
  CSS layout changes (flex-direction reversal, text-align). When adding RTL, the
  `html_lang` context key should be extended to an `html_attrs` dict that includes
  `lang` + `dir`, and all three templates updated accordingly. This is a contained
  change that does not affect the label system.
