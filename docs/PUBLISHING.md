# Publishing & Team Setup Guide

This guide covers two things:

1. **Publishing** — how to push the repo to GitHub and register the skill in the vercel-labs/agent-skills registry
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

For the full setup (CLI + skill in one step), share `install.sh`:

```bash
curl -fsSL https://raw.githubusercontent.com/julioccorderoc/doc-generator/master/install.sh | bash
```

The installer handles cloning, `uv sync`, pango, and writing a path-correct `SKILL.md` to `~/.claude/skills/doc-generator/`. Re-running is idempotent.

### Step 3 — Submit to the vercel-labs/agent-skills registry (optional, for public discoverability)

This step lets anyone install the skill without knowing your GitHub username:

```bash
npx skills add agent-skills --skill doc-generator
```

**To submit:**

1. Fork [github.com/vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) — done: `julioccorderoc/agent-skills` exists
2. In your fork, create `skills/doc-generator/SKILL.md` with the contents of this repo's `SKILL.md`
3. Open a PR to `vercel-labs/agent-skills` — automated via `sync-skill.yml` (see Step 4)
4. Once merged, update the install command in `README.md`:

   ```bash
   npx skills add agent-skills --skill doc-generator
   ```

### Step 4 — Keep the registry in sync (after future SKILL.md changes)

The workflow `.github/workflows/sync-skill.yml` is already live. Every push to `master` that touches `SKILL.md` automatically opens (or updates) a PR to `vercel-labs/agent-skills`.

**Required secret:** `AGENT_SKILLS_PAT` in the doc-generator repo → Settings → Secrets → Actions.

**Important:** Use a **classic PAT** (not fine-grained). Fine-grained tokens cannot create PRs on repos owned by other accounts (`vercel-labs`). A classic PAT with `repo` scope works for both pushing to your fork and opening cross-repo PRs.

Token scopes needed:

- Repository access: `julioccorderoc/agent-skills` (your fork)
- Permission: `repo` (classic) — covers Contents write + Pull requests write

The workflow:

- Force-pushes to a `sync-doc-generator-YYYYMMDD` branch on your fork (safe: ephemeral sync branch)
- Opens a PR to `vercel-labs/agent-skills`, or skips silently if one already exists for that branch

```yaml
name: Sync SKILL.md to agent-skills registry

on:
  push:
    branches: [master]
    paths: [SKILL.md]

jobs:
  open-sync-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure git
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"

      - name: Clone agent-skills fork and update
        env:
          GH_TOKEN: ${{ secrets.AGENT_SKILLS_PAT }}
        run: |
          BRANCH="sync-doc-generator-$(date +%Y%m%d)"

          git clone https://x-access-token:${GH_TOKEN}@github.com/julioccorderoc/agent-skills.git
          cd agent-skills

          # Create or reset the sync branch from main
          git checkout -B "$BRANCH"

          mkdir -p skills/doc-generator
          cp ../SKILL.md skills/doc-generator/SKILL.md

          git add skills/doc-generator/SKILL.md
          git commit -m "sync: update doc-generator SKILL.md from source repo"
          git push origin HEAD --force

          gh pr create \
            --repo vercel-labs/agent-skills \
            --title "sync: update doc-generator SKILL.md" \
            --body "Automated sync from https://github.com/julioccorderoc/doc-generator" \
            --head "julioccorderoc:${BRANCH}" \
            || echo "PR already open for ${BRANCH} — branch updated in place."
```

---

## Part 2 — Team Member Setup

Share this section with coworkers. It covers everything needed to go from zero to generating PDFs with the skill.

---

### Option A — One-command setup (recommended)

Handles everything: clones the repo, installs Python dependencies, installs Pango on macOS, and writes the skill to Claude Code.

```bash
curl -fsSL https://raw.githubusercontent.com/julioccorderoc/doc-generator/master/install.sh | bash
```

Or clone and run directly:

```bash
git clone https://github.com/julioccorderoc/doc-generator.git
cd doc-generator && ./install.sh
```

**To update later:** just re-run the same command. It pulls the latest and refreshes the skill.

---

### Option B — Manual setup

Use this if you prefer step-by-step control.

#### What you need

| Requirement | Notes |
| --- | --- |
| **Claude Code** | The CLI AI agent from Anthropic. Install via [claude.ai/download](https://claude.ai/download) |
| **Node.js** | For `npx skills add`. Version 18+ recommended. Install via [nodejs.org](https://nodejs.org) or `brew install node` |
| **Python 3.11+** | For the doc-generator CLI. Most Macs already have this. |
| **uv** | Python package manager. Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Pango** (macOS only) | System font library required by WeasyPrint. Install once: `brew install pango` |
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

> **Troubleshooting:** If you get a `libpango` error, run `brew install pango` first.

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
npx skills update          # updates SKILL.md instructions
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

The generated PDFs land in `output/` inside the project directory.

---

## Quick reference

| Task | Command |
| --- | --- |
| Full setup (one command) | `curl -fsSL https://raw.githubusercontent.com/julioccorderoc/doc-generator/master/install.sh \| bash` |
| Install skill only | `npx skills add julioccorderoc/doc-generator` |
| Update everything | Re-run `install.sh` or `npx skills update` + `git pull origin master` |
| Check for skill updates | `npx skills check` |
| Generate a PO manually | `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py --doc_type purchase_order --payload <path>` |
| Generate an invoice manually | `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py --doc_type invoice --payload <path>` |
| Open last generated PDF | `open output/$(ls -t output/ \| head -1)` |
