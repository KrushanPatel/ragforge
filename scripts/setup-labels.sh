#!/usr/bin/env bash
# Create or update Ragforge's standard issue/PR labels with the GitHub CLI.
# Running it more than once is safe: existing labels are updated in place (--force).
#
# Usage: scripts/setup-labels.sh [owner/repo]   (defaults to the current repo)
# Requires: gh, authenticated with write access (gh auth login).
set -euo pipefail

repo="${1:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"

# name|color|description
labels=(
  "good first issue|7057ff|Small, self-contained, and well described: a good place to start"
  "help wanted|008672|Extra attention or an outside contributor is welcome"
  "bug|d73a4a|Something isn't working"
  "enhancement|a2eeef|New feature or request"
  "documentation|0075ca|Improvements or additions to documentation"
  "question|d876e3|Further information is requested"
  "needs triage|fbca04|Not yet reviewed by a maintainer"
  "breaking change|b60205|Changes existing behavior or public interfaces"
  "dependencies|0366d6|Dependency updates (Dependabot)"
  "ci|5319e7|CI, workflows, and repository automation"
  "tests|c2e0c6|Adds or changes tests"
  "stale|ededed|No recent activity; will be closed soon"
)

for entry in "${labels[@]}"; do
  IFS='|' read -r name color description <<<"$entry"
  gh label create "$name" --repo "$repo" --color "$color" --description "$description" --force
done

echo "Labels are up to date in $repo."
