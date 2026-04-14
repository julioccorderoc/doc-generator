# 005 — Skill Marketplace Publishing: GitHub-First + Option A (vercel-labs/agent-skills)

**Status:** Accepted
**Date:** 2026-03-16

## Context

`SKILL.md` defines Claude's operating instructions for doc-generator — trigger conditions, data collection protocol, CLI invocation, output presentation. Already written and working locally. Next goal: installable by coworkers (and eventually broader community) without manually copying files.

[`npx skills`](https://github.com/vercel-labs/skills) CLI installs skills from two source types:

1. **GitHub repos** — `npx skills add owner/repo` clones and installs via symlink. `npx skills update` pulls latest commit. Stays permanently connected to source repo.

2. **Registry collections** — curated repos (e.g. `vercel-labs/agent-skills`) bundling many skills. Users install by skill name: `npx skills add agent-skills --skill doc-generator`. Registry entry is a copy, must be synced via PRs.

### Option A — GitHub-first, then vercel-labs/agent-skills registry

**Immediate (team):** Once repo is public, coworkers install with:

```bash
npx skills add <github-username>/doc-generator
```

Symlink model means every `npx skills update` fetches latest `SKILL.md`. No packaging, no release process, no version tags. GitHub repo is single source of truth.

**Discoverability (later):** Submit PR to [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) with `skills/doc-generator/SKILL.md`. Once merged, users install without knowing GitHub username:

```bash
npx skills add agent-skills --skill doc-generator
```

Tradeoff: registry entry is a copy, not live link. Updates need new PR. Automatable with GitHub Actions (see `docs/PUBLISHING.md`).

**Pros:**
- Zero packaging overhead — repo is immediately installable
- Symlink install means coworkers always get current `SKILL.md` via `npx skills update`
- Registry PR is one-time effort improving discoverability without blocking team use
- Works today, before any PR merged

**Cons:**
- Install command includes GitHub username (less memorable for public)
- Registry entry requires manual or automated sync PRs when `SKILL.md` changes
- Coworkers still need full local environment (Python, uv, pango, repo clone)

### Option B — npm package

Publish npm package (e.g. `doc-generator-skill`) containing only `SKILL.md`:

```bash
npx skills add --npm doc-generator-skill
```

**Pros:**
- Clean short install command, no GitHub username
- Standard semantic versioning — teams can pin versions
- npm provides searchable registry independent of GitHub
- Decouples skill versioning from rest of repo

**Cons:**
- Requires npm account + publish workflow
- Each SKILL.md update requires version bump + `npm publish`
- Adds second distribution channel to maintain
- No symlink/auto-update — users get installed version until explicit upgrade
- Premature at this stage

## Decision

**Option A.** GitHub-based install for team immediately. PR to `vercel-labs/agent-skills` for registry discoverability once repo is public. Automate registry sync with GitHub Actions.

Option B documented here as valid future path if skill is packaged independently. Not right now — adds maintenance overhead without solving team's actual problem (simple distribution over shared GitHub repo).

## Consequences

- GitHub repo must be **public** for `npx skills add` to work for coworkers without org-level access.
- `SKILL.md` changes propagate automatically to all installed team members on next `npx skills update`. No versioning ceremony.
- `vercel-labs/agent-skills` registry entry requires sync PR when `SKILL.md` changes. Addressed with GitHub Actions workflow (`.github/workflows/sync-skill.yml`).
- Installing skill only installs *instructions*. Coworkers still need full local environment: Python, `uv`, `pango` (macOS), repo cloned. See `docs/PUBLISHING.md` for full setup guide.
- If Option B pursued later, npm package should contain only `SKILL.md` + `package.json`. Should not bundle Python CLI — separate concerns.

---

## Implementation Notes

*Added 2026-03-17 — learnings from actual rollout.*

### `install.sh` mitigates local environment con

Original con "Coworkers need full local environment" addressed by `install.sh` — one-command curl/bash installer handling cloning, `uv sync`, pango, and SKILL.md installation. Makes Option A as frictionless as Option B for first-time setup.

### `SKILL.md` must use path placeholder, not hardcoded path

`npx skills add` installs SKILL.md as-is. SKILL.md contains project root path for CLI invocation. Hardcoded path (e.g. `/Users/juliocordero/...`) breaks for other users. Solution: `{{PROJECT_ROOT}}` placeholder; `install.sh` substitutes with real path via `sed`. Means `install.sh` is authoritative install path — `npx skills add` installs unsubstituted SKILL.md that won't work until path is patched.

### GitHub Actions sync requires classic PAT, not fine-grained token

Fine-grained PATs scoped to repos owned by token holder. Cannot create PRs on repos owned by other accounts (`vercel-labs/agent-skills`). Classic PAT with `repo` scope required. Secret: `AGENT_SKILLS_PAT` in doc-generator repo Actions secrets.

### Sync workflow must force-push

Workflow uses date-based branch name (`sync-doc-generator-YYYYMMDD`). If workflow runs more than once per day, second push rejected as non-fast-forward. Fix: `git push origin HEAD --force`. Safe — sync branch is ephemeral and ours. If PR already open, `gh pr create` errors — handled with `|| echo` so step succeeds and existing PR gets updated commits.
