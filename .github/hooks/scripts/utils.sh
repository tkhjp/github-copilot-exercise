#!/usr/bin/env bash
# Shared utilities for Copilot CLI hook scripts.
# All hook scripts receive JSON via stdin from the Copilot CLI agent.

# Read stdin JSON into a variable. Call once at script start.
read_hook_input() {
  HOOK_INPUT="$(cat)"
  export HOOK_INPUT
}

# Extract a field from HOOK_INPUT using jq.
# Usage: get_field '.toolName'
get_field() {
  echo "$HOOK_INPUT" | jq -r "$1"
}

# Extract nested field, returning empty string if missing.
# Usage: get_field_safe '.toolArgs.command'
get_field_safe() {
  echo "$HOOK_INPUT" | jq -r "$1 // empty" 2>/dev/null || true
}

# Resolve audit log directory using CLAUDE_PROJECT_DIR (v1.114) or cwd fallback.
get_audit_dir() {
  local base="${CLAUDE_PROJECT_DIR:-$(get_field '.cwd')}"
  echo "${base}/.copilot-audit"
}

# Append a JSON object as one line to a JSONL file.
# Usage: append_jsonl "$json_line" "$file_path"
append_jsonl() {
  local json="$1"
  local file="$2"
  mkdir -p "$(dirname "$file")"
  echo "$json" >> "$file"
}
