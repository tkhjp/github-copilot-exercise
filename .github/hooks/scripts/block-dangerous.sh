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

# Rule 1: Block rm -rf (any flag order) targeting root or broad paths
if echo "$CMD" | grep -Eq 'rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s|rm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] Recursive force-delete (rm -rf) is prohibited. Use targeted rm instead."}'
  exit 0
fi

# Rule 2: Block destructive SQL
if echo "$CMD" | grep -Eiq 'DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE\s+TABLE|DELETE\s+FROM\s+[a-zA-Z]+\s*;'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] Destructive SQL (DROP/TRUNCATE/unqualified DELETE) is prohibited."}'
  exit 0
fi

# Rule 3: Block reading .env files
if echo "$CMD" | grep -Eq '(cat|less|more|head|tail|vim|nano|code)\s+.*\.env'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] Direct reading of .env files is prohibited. Use .env.example as reference."}'
  exit 0
fi

# Default: allow (no output = passthrough)
exit 0
