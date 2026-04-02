#!/usr/bin/env bash
# Shared utilities for Copilot hook scripts.
# Works with both Copilot CLI (camelCase fields) and VS Code Agent hooks (snake_case fields).

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

# --- Dual-field extraction: CLI (camelCase) + VS Code (snake_case) ---

# Get tool name from either format.
get_tool_name() {
  local name
  name="$(echo "$HOOK_INPUT" | jq -r '.toolName // .tool_name // empty')"
  echo "${name:-unknown}"
}

# Get tool input/args from either format.
get_tool_input() {
  echo "$HOOK_INPUT" | jq -c '.toolArgs // .tool_input // {}'
}

# Get tool result from either format.
get_tool_result() {
  echo "$HOOK_INPUT" | jq -c '.toolResult // .tool_response // {}'
}

# Extract file path from tool input (tries multiple possible field names).
get_file_path() {
  local input
  input="$(get_tool_input)"
  echo "$input" | jq -r '.file_path // .filePath // .path // .file // .uri // empty' 2>/dev/null || true
}

# Extract command from tool input (for shell/terminal tools).
get_command() {
  local input
  input="$(get_tool_input)"
  echo "$input" | jq -r '.command // .input // empty' 2>/dev/null || true
}

# Output a permission decision in both CLI and VS Code formats.
# Usage: emit_decision "deny" "Reason text here"
#        emit_decision "ask" "Reason text here"
emit_decision() {
  local decision="$1"
  local reason="$2"
  jq -c -n \
    --arg d "$decision" \
    --arg r "$reason" \
    '{
      permissionDecision: $d,
      permissionDecisionReason: $r,
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        decision: $d,
        reason: $r
      }
    }'
}

# Resolve audit log directory using CLAUDE_PROJECT_DIR (v1.114) or cwd fallback.
get_audit_dir() {
  local cwd
  cwd="$(echo "$HOOK_INPUT" | jq -r '.cwd // .working_directory // empty' 2>/dev/null || true)"
  local base="${CLAUDE_PROJECT_DIR:-$cwd}"
  echo "${base:-.}/.copilot-audit"
}

# Append a JSON object as one line to a JSONL file.
# Usage: append_jsonl "$json_line" "$file_path"
append_jsonl() {
  local json="$1"
  local file="$2"
  mkdir -p "$(dirname "$file")"
  echo "$json" >> "$file"
}
