#!/usr/bin/env bash
# Manual diagnostic: check if dev-team dashboard is stale.
# Not used by hooks (inlined in SKILL.md frontmatter).
# Usage: CLAUDE_PROJECT_DIR=/path/to/project bash check-dashboard.sh
set -euo pipefail
cat > /dev/null

project_root="${CLAUDE_PROJECT_DIR:-.}"
af="$project_root/.dev-team-artifacts"
slug=$(cat "$af/.active-team" 2>/dev/null)
[ -z "$slug" ] && { echo '{}'; exit 0; }
f="$af/$slug/dashboard.html"
[ -f "$f" ] || { echo '{}'; exit 0; }
if [[ "${OSTYPE:-linux}" == darwin* ]]; then
  mt=$(stat -f %m "$f")
else
  mt=$(stat -c %Y "$f")
fi
age=$(( $(date +%s) - mt ))
if [ "$age" -gt 120 ]; then
  echo "DASHBOARD STALE ($((age/60))m) -- regenerate NOW: $f" >&2
fi
echo '{}'
