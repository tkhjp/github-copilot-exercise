#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

AUDIT_DIR="$(get_audit_dir)"
TIMESTAMP="$(get_field '.timestamp')"
TOOL_NAME="$(get_field '.toolName')"
TOOL_ARGS="$(get_field '.toolArgs')"
CWD="$(get_field '.cwd')"

ENTRY=$(jq -c -n \
  --arg ts "$TIMESTAMP" \
  --arg tool "$TOOL_NAME" \
  --arg cwd "$CWD" \
  --argjson args "$TOOL_ARGS" \
  '{timestamp:$ts, event:"preToolUse", tool:$tool, args:$args, cwd:$cwd}')

append_jsonl "$ENTRY" "$AUDIT_DIR/pretool.jsonl"

# Audit hooks must not block — no stdout output
exit 0
