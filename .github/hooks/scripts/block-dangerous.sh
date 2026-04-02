#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

TOOL_NAME="$(get_tool_name)"
FILE_PATH="$(get_file_path)"
CMD="$(get_command)"

# Rule 1: Block editing .env files (any tool that touches .env)
if [[ -n "$FILE_PATH" ]] && echo "$FILE_PATH" | grep -qE '\.env($|\.)'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] .env ファイルの編集は禁止されています。.env.example を参照してください。"}'
  exit 0
fi

# Rule 2: Block editing deploy/production files
if [[ -n "$FILE_PATH" ]] && echo "$FILE_PATH" | grep -qEi 'deploy|prod|\.secret'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] デプロイ・本番環境関連ファイルの直接編集は禁止されています。"}'
  exit 0
fi

# Rule 3: Block shell commands that suppress output (hiding evidence)
if [[ -n "$CMD" ]] && echo "$CMD" | grep -qE '>\s*/dev/null|2>&1\s*/dev/null'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] 出力の抑制（/dev/null へのリダイレクト）は監査上禁止されています。"}'
  exit 0
fi

# Rule 4: Block rm -rf (keep as safety net)
if [[ -n "$CMD" ]] && echo "$CMD" | grep -qE 'rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s|rm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s'; then
  echo '{"permissionDecision":"deny","permissionDecisionReason":"[Policy] rm -rf は禁止されています。"}'
  exit 0
fi

# Default: allow (no output = passthrough)
exit 0
