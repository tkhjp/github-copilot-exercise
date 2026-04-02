#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

TOOL_NAME="$(get_field '.toolName')"

# Only inspect bash/shell tool calls
if [[ "$TOOL_NAME" != "bash" && "$TOOL_NAME" != "shell" ]]; then
  exit 0
fi

CMD="$(get_field_safe '.toolArgs.command')"
if [[ -z "$CMD" ]]; then
  exit 0
fi

# Rule 1: git push --force — risky but sometimes intentional
if echo "$CMD" | grep -Eq 'git\s+push\s+.*--force|git\s+push\s+-f'; then
  echo '{"permissionDecision":"ask","permissionDecisionReason":"[Escalation] Force push detected. This rewrites remote history and may affect other developers. Confirm to proceed."}'
  exit 0
fi

# Rule 2: git push to main/master — should usually go through PR
if echo "$CMD" | grep -Eq 'git\s+push\s+\S+\s+(main|master)'; then
  echo '{"permissionDecision":"ask","permissionDecisionReason":"[Escalation] Direct push to main/master detected. Consider using a pull request instead. Confirm to proceed."}'
  exit 0
fi

# Rule 3: chmod 777 — overly permissive
if echo "$CMD" | grep -Eq 'chmod\s+777'; then
  echo '{"permissionDecision":"ask","permissionDecisionReason":"[Escalation] chmod 777 grants full access to all users. Consider more restrictive permissions (e.g., 755). Confirm to proceed."}'
  exit 0
fi

# Default: allow
exit 0
