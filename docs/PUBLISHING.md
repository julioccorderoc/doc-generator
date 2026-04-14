# Publishing & Team Setup Guide

This guide covers two things:

1. **Publishing** — how to push the repo to GitHub and share the skill
2. **Team setup** — step-by-step instructions to share with coworkers so they can install and use the skill

---

## Part 1 — Publishing the Skill

### Prerequisites

- The doc-generator repo is on GitHub and **public** (private repos require org-level credentials for `npx skills add` to work for others)
- You have push access to the repo

### Step 1 — Push the repo to GitHub

If you haven't already:

```bash
# From the project root
git remote add origin https://github.com/julioccorderoc/doc-generator.git
git push -u origin master
```

Nothing special is needed — the `SKILL.md` at the root is what `npx skills add` looks for.

### Step 2 — Share the install command with your team

Once the repo is public, team members can install the skill with:

```bash
npx skills add julioccorderoc/doc-generator
```

For the full setup (CLI + skill), share the manual setup steps in Part 2 below.

---

## Part 2 — Team Member Setup

Share this section with coworkers. It covers everything needed to go from zero to generating PDFs with the skill.

---

### Manual setup

#### What you need

| Requirement | Notes |
| --- | --- |
| **Claude Code** | The CLI AI agent from Anthropic. Install via [claude.ai/download](https://claude.ai/download) |
| **Node.js** | For `npx skills add`. Version 18+ recommended. Install via [nodejs.org](https://nodejs.org) or `brew install node` |
| **Python 3.11+** | For the doc-generator CLI. Most Macs already have this. |
| **uv** | Python package manager. Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Pango** | System font library required by WeasyPrint. Install once (macOS): `brew install pango` or (Debian): `sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0` |
| **The repo** | Cloned to your machine (see Step 1 below) |

#### Step 1 — Clone the repo

```bash
git clone https://github.com/julioccorderoc/doc-generator.git
cd doc-generator
```

#### Step 2 — Install Python dependencies

```bash
uv sync
```

#### Step 3 — Verify the CLI works

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order \
  --payload tests/fixtures/sample_po.json \
  --preview
```

Expected: a PDF opens showing a green-header Purchase Order.

> **Troubleshooting:** If you get a `libpango` error, run `brew install pango` (macOS) or `sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0` (Debian) first.

#### Step 4 — Install the skill into Claude Code

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
git pull origin master     # updates the CLI and templates
```

---

### Step 6 — Use it

Just describe what you want in natural language. Examples:

> "Make a purchase order for Acme Ingredients — 50 kg of Ashwagandha at $24/kg and 25 kg of Magnesium Glycinate at $18.50/kg. Net 30 terms, FedEx Ground."
>
> "Invoice our client Acme Retail for 8 hours of consulting at $200/hr and a label design for 2 SKUs at $375 each. Due April 15."

Claude will:

1. Identify what's already provided
2. Ask for any missing required fields in one pass
3. Apply smart defaults (today's date, USD, zero tax) silently
4. Show a confirmation summary
5. Generate the PDF and tell you the output path and grand total

The generated PDFs land in your current working directory by default. When using the skill manually via CLI, you can control the location with `--output_dir <path>`; omitting it falls back to `output/` inside the project directory.

---

## Quick reference

| Task | Command |
| --- | --- |
| Install skill | `npx skills add julioccorderoc/doc-generator` |
| Update skill | `npx skills update -g` |
| Update CLI | `git pull origin master` (inside your clone) |
| Check for skill updates | `npx skills check` |
| Generate a PO manually | `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py --doc_type purchase_order --payload <path>` |
| Generate an invoice manually | `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py --doc_type invoice --payload <path>` |
| Open last generated PDF | `open output/$(ls -t output/ \| head -1)` |
