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

Once the repo is public, team members can install with:

```bash
npx skills add julioccorderoc/doc-generator
```

That's it. Share this command in your team's Slack/Notion/onboarding doc. The `npx skills add` command clones the repo and creates a symlink — no further action needed after that.

### Step 3 — Submit to the vercel-labs/agent-skills registry (optional, for public discoverability)

This step lets anyone install the skill without knowing your GitHub username:

```bash
npx skills add agent-skills --skill doc-generator
```

**To submit:**

1. Fork [github.com/vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills)
2. In your fork, create `skills/doc-generator/SKILL.md` with the contents of this repo's `SKILL.md`
3. Open a PR to `vercel-labs/agent-skills` with this description:

   > **doc-generator** — Generates professional PDF business documents (purchase orders, invoices) from user-provided data via a local CLI. Claude handles conversational data collection; the CLI handles rendering. Requires local installation of the doc-generator CLI.
   >
   > Source repo: `https://github.com/julioccorderoc/doc-generator`

4. Once merged, update the install command in `README.md`:

   ```bash
   npx skills add agent-skills --skill doc-generator
   ```

### Step 4 — Keep the registry in sync (after future SKILL.md changes)

The registry entry in `vercel-labs/agent-skills` is a copy, not a live link. When you update `SKILL.md` in this repo, you need to open a new PR to `agent-skills` with the updated content.

To automate this, create `.github/workflows/sync-skill.yml`:

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
          # Clone your fork of vercel-labs/agent-skills
          git clone https://x-access-token:${GH_TOKEN}@github.com/julioccorderoc/agent-skills.git
          cd agent-skills

          # Create or update the skill file
          mkdir -p skills/doc-generator
          cp ../SKILL.md skills/doc-generator/SKILL.md

          # Commit and push to a sync branch
          git checkout -b sync-doc-generator-$(date +%Y%m%d)
          git add skills/doc-generator/SKILL.md
          git commit -m "sync: update doc-generator SKILL.md from source repo"
          git push origin HEAD

          # Open PR using gh CLI
          gh pr create \
            --repo vercel-labs/agent-skills \
            --title "sync: update doc-generator SKILL.md" \
            --body "Automated sync from https://github.com/julioccorderoc/doc-generator" \
            --head "julioccorderoc:sync-doc-generator-$(date +%Y%m%d)"
```

**Required secrets:** Add a `AGENT_SKILLS_PAT` secret in your repo settings — a GitHub Personal Access Token with `repo` scope on your `agent-skills` fork.

---

## Part 2 — Team Member Setup

Share this section with coworkers. It covers everything needed to go from zero to generating PDFs with the skill.

---

### What you need

| Requirement | Notes |
| --- | --- |
| **Claude Code** | The CLI AI agent from Anthropic. Install via [claude.ai/download](https://claude.ai/download) |
| **Node.js** | For `npx skills add`. Version 18+ recommended. Install via [nodejs.org](https://nodejs.org) or `brew install node` |
| **Python 3.11+** | For the doc-generator CLI. Most Macs already have this. |
| **uv** | Python package manager. Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Pango** (macOS only) | System font library required by WeasyPrint. Install once: `brew install pango` |
| **The repo** | Cloned to your machine (see Step 1 below) |

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/julioccorderoc/doc-generator.git
cd doc-generator
```

### Step 2 — Install Python dependencies

```bash
uv sync
```

This installs WeasyPrint, Jinja2, and Pydantic into a local virtual environment. Takes about 30 seconds on the first run.

### Step 3 — Verify the CLI works

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py \
  --doc_type purchase_order \
  --payload tests/fixtures/sample_po.json \
  --preview
```

Expected: a PDF opens in your viewer showing a green-header Purchase Order. If you see output like `output/purchase_order_20260316_0001.pdf`, it worked.

> **Troubleshooting:** If you get a `libpango` error, run `brew install pango` first.

### Step 4 — Install the skill into Claude Code

```bash
npx skills add julioccorderoc/doc-generator
```

This clones the repo's `SKILL.md` into your `~/.claude/skills/doc-generator/` directory as a symlink. Claude Code picks it up automatically — no restart required.

Verify the skill is installed:

```text
(in Claude Code)
What skills are available?
```

You should see `doc-generator` in the list with its description.

### Step 5 — Use it

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

### Step 6 — Staying up to date

When the skill's instructions are updated, pull the latest:

```bash
npx skills update
```

This runs `git pull` on the cloned `SKILL.md` repo. The PDF templates and CLI are part of the main repo — pull those separately:

```bash
git pull origin master
```

---

## Quick reference

| Task | Command |
| --- | --- |
| Install skill from GitHub | `npx skills add <owner>/doc-generator` |
| Check for skill updates | `npx skills check` |
| Pull latest skill instructions | `npx skills update` |
| Generate a PO manually | `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py --doc_type purchase_order --payload <path>` |
| Generate an invoice manually | `DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python scripts/generate.py --doc_type invoice --payload <path>` |
| Open last generated PDF | `open output/$(ls -t output/ \| head -1)` |
