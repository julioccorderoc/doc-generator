# Publishing & Team Setup Guide

Covers two things:

1. **Publishing** — push repo to GitHub and share skill
2. **Team setup** — step-by-step for coworkers to install and use

---

## Part 1 — Publishing the Skill

### Prerequisites

- doc-generator repo on GitHub and **public** (private repos require org-level credentials for `npx skills add`)
- You have push access

### Step 1 — Push repo to GitHub

If not already done:

```bash
# From project root
git remote add origin https://github.com/julioccorderoc/doc-generator.git
git push -u origin master
```

Nothing special needed — `SKILL.md` at root is what `npx skills add` looks for.

### Step 2 — Share install command with team

Once repo is public:

```bash
npx skills add julioccorderoc/doc-generator
```

For full setup (CLI + skill), share manual steps in Part 2 below.

---

## Part 2 — Team Member Setup

Share this section with coworkers. Covers everything needed to go from zero to generating PDFs.

---

### Manual setup

#### What you need

| Requirement | Notes |
| --- | --- |
| **Claude Code** | CLI AI agent from Anthropic. Install via [claude.ai/download](https://claude.ai/download) |
| **Node.js** | For `npx skills add`. Version 18+. Install via [nodejs.org](https://nodejs.org) or `brew install node` |
| **Python 3.11+** | For doc-generator CLI. Most Macs already have this. |
| **uv** | Python package manager. Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Pango** | System font library for WeasyPrint. macOS: `brew install pango` / Debian: `sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0` |
| **The repo** | Cloned to your machine (Step 1 below) |

#### Step 1 — Clone repo

```bash
git clone https://github.com/julioccorderoc/doc-generator.git
cd doc-generator
```

#### Step 2 — Install Python dependencies

```bash
uv sync
```

#### Step 3 — Verify CLI works

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order \
  --payload tests/fixtures/sample_po.json \
  --preview
```

Expected: PDF opens showing green-header Purchase Order.

> **Troubleshooting:** If you get `libpango` error, run `brew install pango` (macOS) or `sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0` (Debian) first.

#### Step 4 — Install skill into Claude Code

```bash
npx skills add julioccorderoc/doc-generator
```

Verify:

```text
(in Claude Code)
What skills are available?
```

You should see `doc-generator` in the list.

#### Step 5 — Staying up to date

```bash
npx skills update -g       # updates SKILL.md instructions (installed globally)
git pull origin master     # updates CLI and templates
```

---

### Step 6 — Use it

Describe what you want in natural language:

> "Make a purchase order for Acme Ingredients — 50 kg of Ashwagandha at $24/kg and 25 kg of Magnesium Glycinate at $18.50/kg. Net 30 terms, FedEx Ground."
>
> "Invoice our client Acme Retail for 8 hours of consulting at $200/hr and a label design for 2 SKUs at $375 each. Due April 15."

Claude will:

1. Identify what's already provided
2. Ask for missing required fields in one pass
3. Apply smart defaults (today's date, USD, zero tax) silently
4. Show confirmation summary
5. Generate PDF and report output path + grand total

Generated PDFs land in current working directory by default. Via CLI, control location with `--output_dir <path>`; omitting falls back to `output/` inside project directory.

---

## Quick reference

| Task | Command |
| --- | --- |
| Install skill | `npx skills add julioccorderoc/doc-generator` |
| Update skill | `npx skills update -g` |
| Update CLI | `git pull origin master` (inside your clone) |
| Check for updates | `npx skills check` |
| Generate PO manually | `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py --doc_type purchase_order --payload <path>` |
| Generate invoice manually | `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py --doc_type invoice --payload <path>` |
| Open last generated PDF | `open output/$(ls -t output/ \| head -1)` |
