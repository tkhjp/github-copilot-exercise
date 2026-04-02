#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

AUDIT_DIR="$(get_audit_dir)"

# Raw dump for diagnostics (see actual field names from VS Code / CLI)
append_jsonl "$HOOK_INPUT" "$AUDIT_DIR/raw-pretool.jsonl"

# Structured entry using dual-field extraction
TOOL_NAME="$(get_tool_name)"
TOOL_INPUT="$(get_tool_input)"
TIMESTAMP="$(get_field_safe '.timestamp')"
CWD="$(get_field_safe '.cwd')"

ENTRY=$(jq -c -n \
  --arg ts "${TIMESTAMP:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}" \
  --arg tool "$TOOL_NAME" \
  --arg cwd "$CWD" \
  --argjson args "$TOOL_INPUT" \
  '{timestamp:$ts, event:"preToolUse", tool:$tool, args:$args, cwd:$cwd}')

append_jsonl "$ENTRY" "$AUDIT_DIR/pretool.jsonl"

# Audit hooks must not block — no stdout output
exit 0
