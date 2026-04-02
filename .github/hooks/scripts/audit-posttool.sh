#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

AUDIT_DIR="$(get_audit_dir)"
TOOL_NAME="$(get_field '.toolName')"
RESULT_TYPE="$(get_field_safe '.toolResult.resultType')"
RESULT_TEXT="$(get_field_safe '.toolResult.textResultForLlm')"

# Truncate long results to keep audit log manageable
RESULT_TRUNCATED="${RESULT_TEXT:0:500}"

ENTRY=$(jq -c -n \
  --arg tool "$TOOL_NAME" \
  --arg rt "$RESULT_TYPE" \
  --arg txt "$RESULT_TRUNCATED" \
  '{timestamp:(now|todate), event:"postToolUse", tool:$tool, resultType:$rt, resultPreview:$txt}')

append_jsonl "$ENTRY" "$AUDIT_DIR/posttool.jsonl"

# Audit hooks must not block — no stdout output
exit 0
