#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

AUDIT_DIR="$(get_audit_dir)"
TOOL_NAME="$(get_field '.toolName')"

# postToolUseFailure input fields — may include error details
# The exact field names depend on CLI version; extract what's available
ERROR_MSG="$(get_field_safe '.error.message')"
ERROR_NAME="$(get_field_safe '.error.name')"
TOOL_ARGS="$(get_field_safe '.toolArgs')"

ENTRY=$(jq -c -n \
  --arg tool "$TOOL_NAME" \
  --arg err_name "$ERROR_NAME" \
  --arg err_msg "$ERROR_MSG" \
  --arg args "$TOOL_ARGS" \
  '{timestamp:(now|todate), event:"postToolUseFailure", tool:$tool, errorName:$err_name, errorMessage:$err_msg, args:$args}')

append_jsonl "$ENTRY" "$AUDIT_DIR/failures.jsonl"

# Log to stderr for visibility during demo
echo "[Hook] Tool failure logged: $TOOL_NAME — $ERROR_MSG" >&2

# Audit hooks must not block — no stdout output
exit 0
