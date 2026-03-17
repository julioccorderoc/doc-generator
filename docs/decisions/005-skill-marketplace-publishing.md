# 005 — Skill Marketplace Publishing: GitHub-First + Option A (vercel-labs/agent-skills)

**Status:** Accepted
**Date:** 2026-03-16

## Context

`SKILL.md` defines Claude's operating instructions for the doc-generator — trigger conditions, data collection protocol, CLI invocation, and output presentation. It is already written and working locally. The next goal is to make it installable by coworkers (and eventually the broader community) without requiring them to manually copy files.

The [`npx skills`](https://github.com/vercel-labs/skills) CLI is the established tool for this ecosystem. It installs skills from two source types:

1. **GitHub repositories** — `npx skills add owner/repo` clones the repo and installs via symlink. Running `npx skills update` pulls the latest commit for all tracked repos. The installed skill stays permanently connected to the source repo.

2. **Registry collections** — curated repos (e.g. `vercel-labs/agent-skills`) that bundle many skills. Users install from the collection by skill name: `npx skills add agent-skills --skill doc-generator`. The registry entry is a copy that must be kept in sync with the source via PRs.

Two publishing paths were considered:

### Option A — GitHub-first, then vercel-labs/agent-skills registry

**Immediate (for the team):** Once the repo is public on GitHub, coworkers install with:

```bash
npx skills add <github-username>/doc-generator
```

The symlink model means every subsequent `npx skills update` fetches the latest `SKILL.md` from GitHub. No packaging, no release process, no version tags needed. The GitHub repo is the single source of truth.

**For discoverability (later):** Submit a PR to [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) with `skills/doc-generator/SKILL.md`. Once merged, users can find and install the skill without knowing the GitHub username:

```bash
npx skills add agent-skills --skill doc-generator
```

The tradeoff with the registry entry: it is a copy, not a live link. Updates to `SKILL.md` in this repo do not automatically propagate to the registry — a new PR must be opened. This can be automated with a GitHub Actions workflow (see `docs/PUBLISHING.md`).

**Pros:**
- Zero packaging overhead — the repo is immediately installable
- Symlink install means coworkers always get current `SKILL.md` via `npx skills update`
- Registry PR is a one-time effort that improves discoverability without blocking team use
- Works today, before any PR is merged

**Cons:**
- Install command includes GitHub username (less memorable for public users)
- Registry entry requires manual or automated sync PRs when `SKILL.md` changes
- Coworkers still need the full local environment set up (Python, uv, pango, repo clone)

### Option B — npm package

Publish an npm package (e.g. `doc-generator-skill`) containing only `SKILL.md`. The `npx skills add` CLI would support:

```bash
npx skills add --npm doc-generator-skill
```

**Pros:**
- Clean, short install command with no GitHub username
- Standard semantic versioning — teams can pin to a version
- npm provides a searchable registry independent of GitHub
- Decouples skill versioning from the rest of the repo

**Cons:**
- Requires an npm account and maintaining a publish workflow
- Each SKILL.md update requires a version bump and `npm publish`
- Adds a second distribution channel to maintain alongside the GitHub repo
- No symlink/auto-update mechanism — users get the version they installed until they explicitly upgrade
- More appropriate for a widely-distributed, independently versioned skill; premature at this stage

## Decision

**Option A.** Use GitHub-based install for the team immediately. Submit a PR to `vercel-labs/agent-skills` for registry discoverability once the repo is public. Automate the registry sync with a GitHub Actions workflow.

Option B is documented here and remains a valid future path if the skill is packaged independently (e.g. if it is separated from the doc-generator repo and distributed as a standalone tool). It is not the right choice now because it adds maintenance overhead without solving the team's actual problem, which is simple distribution over a shared GitHub repo.

## Consequences

- The GitHub repo must be **public** for `npx skills add` to work for coworkers without org-level access.
- Any change to `SKILL.md` in the repo propagates automatically to all installed team members on their next `npx skills update`. No versioning ceremony required.
- The `vercel-labs/agent-skills` registry entry requires a sync PR whenever `SKILL.md` changes. This is addressed in Phase 6 of the implementation plan with a GitHub Actions workflow (`.github/workflows/sync-skill.yml`).
- Installing the skill only installs the *instructions*. Coworkers still need the full local environment: Python, `uv`, `pango` (macOS), and the repo cloned. The skill does not ship the Python runtime. See `docs/PUBLISHING.md` for the full setup guide.
- If Option B is pursued in the future, the npm package should contain only `SKILL.md` and a `package.json`. It should not bundle the Python CLI — those are separate concerns.
