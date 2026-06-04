#!/usr/bin/env bash
# Atlas Insight — interactive release script.
# Called by: make release
# What it does:
#   1. Prompts for semantic version + optional title
#   2. Updates VERSION and frontend/package.json
#   3. Git commits + tags
#   4. Builds Docker images (backend + frontend)
#   5. Tags for ghcr.io
#   6. Confirms then pushes images + git tag
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BOLD='\033[1m'; BLUE='\033[0;34m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

banner() { echo -e "\n${BOLD}${BLUE}══ $1 ══${NC}"; }
ok()     { echo -e "  ${GREEN}✓${NC} $1"; }
warn()   { echo -e "  ${YELLOW}!${NC} $1"; }
die()    { echo -e "  ${RED}✗${NC} $1" >&2; exit 1; }
info()   { echo -e "  ${CYAN}→${NC} $1"; }

confirm() {
    printf "${BOLD}%s [Y/n]:${NC} " "${1:-Proceed?}"
    read -r _ans
    [[ -z "$_ans" || "$_ans" =~ ^[Yy]$ ]]
}

# ── Preflight ──────────────────────────────────────────────────────────────────

banner "Atlas Insight — Release"
command -v docker  >/dev/null || die "docker not found"
command -v git     >/dev/null || die "git not found"
command -v node    >/dev/null || die "node not found (needed to update package.json)"

# ── Step 0: Gather inputs ──────────────────────────────────────────────────────

banner "Step 0 — Version"
echo
printf "${BOLD}Semantic version (e.g. 1.0.0):${NC} "
read -r RAW_VERSION
[[ "$RAW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "Version must be X.Y.Z (e.g. 1.0.0)"

echo
printf "${BOLD}Release title (optional, press Enter to skip):${NC} "
read -r RAW_TITLE

# Build tag: v1.0.0 or v1.0.0-my-title
if [[ -n "$RAW_TITLE" ]]; then
    SLUG="$(echo "$RAW_TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')"
    GIT_TAG="v${RAW_VERSION}-${SLUG}"
else
    SLUG=""
    GIT_TAG="v${RAW_VERSION}"
fi

echo
ok "Version:  $RAW_VERSION"
ok "Git tag:  $GIT_TAG"
echo

# ── Derive registry owner from git remote ─────────────────────────────────────

REMOTE_URL="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
if [[ -z "$REMOTE_URL" ]]; then
    warn "No git remote 'origin' found."
    printf "${BOLD}GitHub username (for ghcr.io):${NC} "
    read -r GITHUB_OWNER
else
    # Parse owner from SSH (git@github.com:owner/repo.git) or HTTPS
    if [[ "$REMOTE_URL" =~ github\.com[:/]([^/]+)/ ]]; then
        GITHUB_OWNER="${BASH_REMATCH[1]}"
        # Convert to lowercase (ghcr.io requires lowercase)
        GITHUB_OWNER="${GITHUB_OWNER,,}"
        info "GitHub owner: $GITHUB_OWNER (from remote)"
    else
        warn "Could not parse owner from remote: $REMOTE_URL"
        printf "${BOLD}GitHub username (for ghcr.io):${NC} "
        read -r GITHUB_OWNER
        GITHUB_OWNER="${GITHUB_OWNER,,}"
    fi
fi

REGISTRY="ghcr.io/${GITHUB_OWNER}"
BACKEND_IMAGE="${REGISTRY}/atlas-insight-backend"
FRONTEND_IMAGE="${REGISTRY}/atlas-insight-frontend"

info "Registry:  $REGISTRY"
info "Backend:   ${BACKEND_IMAGE}:${GIT_TAG}"
info "Frontend:  ${FRONTEND_IMAGE}:${GIT_TAG}"

# ── Dirty tree check ───────────────────────────────────────────────────────────

if [[ -n "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null)" ]]; then
    warn "Working tree has uncommitted changes."
    warn "The release commit will include ALL staged + unstaged modifications."
    confirm "Continue anyway?" || { echo "Aborted."; exit 0; }
fi

# ── Step 1: Update version files ──────────────────────────────────────────────

banner "Step 1 — Update version files"

# Update package.json + package-lock.json atomically via npm version.
# --no-git-tag-version: skip npm's own commit/tag — we handle that below.
(cd "$REPO_ROOT/frontend" && npm version "$RAW_VERSION" --no-git-tag-version --allow-same-version)
ok "frontend/package.json + package-lock.json → $RAW_VERSION"

# ── Step 2: Git commit + tag ───────────────────────────────────────────────────

banner "Step 2 — Git commit + tag"

git -C "$REPO_ROOT" add "$REPO_ROOT/frontend/package.json" "$REPO_ROOT/frontend/package-lock.json"
git -C "$REPO_ROOT" commit -m "Updating version for release: ${GIT_TAG}"
ok "Committed: Updating version for release: ${GIT_TAG}"

git -C "$REPO_ROOT" tag "$GIT_TAG"
ok "Tagged: $GIT_TAG"

# ── Step 3: Docker login check ─────────────────────────────────────────────────

banner "Step 3 — Docker registry auth"

if ! docker info 2>/dev/null | grep -q "Username\|Registry"; then
    # Check by attempting a silent login probe
    if ! docker login ghcr.io --get-login > /dev/null 2>&1; then
        info "Not logged in to ghcr.io. Logging in as ${GITHUB_OWNER}..."
        docker login ghcr.io -u "$GITHUB_OWNER" || die "Docker login failed"
    fi
fi
ok "Authenticated with ghcr.io"

# ── Step 4: Build images ───────────────────────────────────────────────────────

banner "Step 4 — Build Docker images"

info "Building backend image..."
docker build \
    --file "$REPO_ROOT/backend/Dockerfile" \
    --tag "atlas-insight-backend:${GIT_TAG}" \
    --tag "${BACKEND_IMAGE}:${GIT_TAG}" \
    "$REPO_ROOT"
ok "Backend image built: ${BACKEND_IMAGE}:${GIT_TAG}"

info "Building frontend image..."
docker build \
    --file "$REPO_ROOT/frontend/Dockerfile" \
    --tag "atlas-insight-frontend:${GIT_TAG}" \
    --tag "${FRONTEND_IMAGE}:${GIT_TAG}" \
    "$REPO_ROOT/frontend"
ok "Frontend image built: ${FRONTEND_IMAGE}:${GIT_TAG}"

# ── Step 5: Summary + confirm push ────────────────────────────────────────────

banner "Step 5 — Push"
echo
echo "  Release: ${GIT_TAG}"
echo
echo "  Images to push:"
printf "    %-60s\n" "${BACKEND_IMAGE}:${GIT_TAG}"
printf "    %-60s\n" "${FRONTEND_IMAGE}:${GIT_TAG}"
echo
echo "  Git:"
echo "    git push              (commit: Updating version for release: ${GIT_TAG})"
echo "    git push --tags       (tag: ${GIT_TAG})"
echo

if confirm "Push everything to ghcr.io and GitHub?"; then
    info "Pushing backend image..."
    docker push "${BACKEND_IMAGE}:${GIT_TAG}"
    ok "Backend pushed"

    info "Pushing frontend image..."
    docker push "${FRONTEND_IMAGE}:${GIT_TAG}"
    ok "Frontend pushed"

    info "Pushing git commit + tag..."
    git -C "$REPO_ROOT" push
    git -C "$REPO_ROOT" push --tags
    ok "Git pushed"

    banner "Release complete"
    echo "  Tag:      ${GIT_TAG}"
    echo "  Backend:  ${BACKEND_IMAGE}:${GIT_TAG}"
    echo "  Frontend: ${FRONTEND_IMAGE}:${GIT_TAG}"
else
    banner "Images built — push skipped"
    echo "  Run these manually when ready:"
    echo ""
    echo "  docker push ${BACKEND_IMAGE}:${GIT_TAG}"
    echo "  docker push ${FRONTEND_IMAGE}:${GIT_TAG}"
    echo "  git push && git push --tags"
fi
