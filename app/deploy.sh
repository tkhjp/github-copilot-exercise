#!/usr/bin/env bash
# Deploy script — pushes current branch to production
# WARNING: This pushes directly to main. Use with caution.
set -euo pipefail

REMOTE="${DEPLOY_REMOTE:-origin}"
BRANCH="${DEPLOY_BRANCH:-main}"

echo "Deploying to $REMOTE/$BRANCH..."
git push "$REMOTE" "$BRANCH"
echo "Deploy complete."
