#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

AUDIT_DIR="$(get_audit_dir)"
TOOL_NAME="$(get_tool_name)"
TOOL_INPUT="$(get_tool_input)"

# Try multiple error field patterns
ERROR_MSG="$(get_field_safe '.error.message')"
if [[ -z "$ERROR_MSG" ]]; then
  ERROR_MSG="$(get_field_safe '.error')"
fi
ERROR_NAME="$(get_field_safe '.error.name')"

ENTRY=$(jq -c -n \
  --arg tool "$TOOL_NAME" \
  --arg err_name "$ERROR_NAME" \
  --arg err_msg "$ERROR_MSG" \
  --argjson args "$TOOL_INPUT" \
  '{timestamp:(now|todate), event:"postToolUseFailure", tool:$tool, errorName:$err_name, errorMessage:$err_msg, args:$args}')

append_jsonl "$ENTRY" "$AUDIT_DIR/failures.jsonl"

# Raw dump for diagnostics
append_jsonl "$HOOK_INPUT" "$AUDIT_DIR/raw-failures.jsonl"

# Log to stderr for visibility during demo
echo "[Hook] Tool failure logged: $TOOL_NAME — $ERROR_MSG" >&2

# Audit hooks must not block — no stdout output
exit 0
