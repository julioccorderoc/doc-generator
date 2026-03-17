#!/usr/bin/env bash
# doc-generator installer
#
# Usage (one-liner):
#   curl -fsSL https://raw.githubusercontent.com/julioccorderoc/doc-generator/master/install.sh | bash
#
# Custom install directory:
#   DOC_GENERATOR_DIR=~/projects/doc-generator \
#     curl -fsSL https://raw.githubusercontent.com/julioccorderoc/doc-generator/master/install.sh | bash
#
# Or clone and run directly:
#   git clone https://github.com/julioccorderoc/doc-generator.git
#   cd doc-generator && ./install.sh

set -euo pipefail

REPO="https://github.com/julioccorderoc/doc-generator.git"
INSTALL_DIR="${DOC_GENERATOR_DIR:-$HOME/doc-generator}"
SKILLS_DIR="$HOME/.claude/skills/doc-generator"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { printf "${GREEN}▶ %s${NC}\n" "$*"; }
warn() { printf "${YELLOW}⚠ %s${NC}\n" "$*"; }
die()  { printf "${RED}✗ %s${NC}\n" "$*" >&2; exit 1; }

# ── 1. Locate or clone the repo ───────────────────────────────────────────────
if [[ -f "scripts/generate.py" && -f "SKILL.md" ]]; then
    INSTALL_DIR="$(pwd)"
    info "Running from inside the repo — using: $INSTALL_DIR"
elif [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Repo already exists at $INSTALL_DIR — updating..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    info "Cloning doc-generator to $INSTALL_DIR..."
    git clone "$REPO" "$INSTALL_DIR"
fi

# ── 2. Python dependencies ────────────────────────────────────────────────────
command -v uv &>/dev/null \
    || die "uv not found. Install it first: curl -LsSf https://astral.sh/uv/install.sh | sh"
info "Installing Python dependencies..."
(cd "$INSTALL_DIR" && uv sync)

# ── 3. macOS system dependency (Pango / WeasyPrint) ──────────────────────────
if [[ "$(uname)" == "Darwin" ]]; then
    if brew list pango &>/dev/null 2>&1; then
        info "pango already installed."
    else
        info "Installing pango (required by WeasyPrint on macOS)..."
        brew install pango
    fi
fi

# ── 4. Install the Claude Code skill ─────────────────────────────────────────
info "Writing skill to $SKILLS_DIR ..."
mkdir -p "$SKILLS_DIR"
sed "s|~/doc-generator|$INSTALL_DIR|g" "$INSTALL_DIR/SKILL.md" > "$SKILLS_DIR/SKILL.md"

# ── 5. Done ───────────────────────────────────────────────────────────────────
printf "\n${GREEN}✓ doc-generator installed successfully!${NC}\n\n"
printf "  Project : %s\n" "$INSTALL_DIR"
printf "  Skill   : %s\n\n" "$SKILLS_DIR/SKILL.md"
printf "  Try it in Claude Code:\n"
printf '    "Make a purchase order for Acme — 50 kg of Ashwagandha at $24/kg, Net 30"\n\n'
printf "  To update to the latest version:\n"
printf "    curl -fsSL https://raw.githubusercontent.com/julioccorderoc/doc-generator/master/install.sh | bash\n\n"
