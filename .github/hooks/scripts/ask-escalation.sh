#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

TOOL_NAME="$(get_tool_name)"
CMD="$(get_command)"

# Only inspect shell/terminal tool calls (broad match for VS Code + CLI)
case "$TOOL_NAME" in
  *terminal*|*shell*|*bash*|*command*|*Terminal*|bash|shell) ;;
  *) exit 0 ;;
esac

[[ -z "$CMD" ]] && exit 0

# Rule 1: git commit — confirm before committing
if echo "$CMD" | grep -qE 'git\s+commit'; then
  echo '{"permissionDecision":"ask","permissionDecisionReason":"[確認] git commit を実行します。コミットメッセージと変更内容を確認してください。"}'
  exit 0
fi

# Rule 2: Package install — confirm dependency changes
if echo "$CMD" | grep -qEi 'pip\s+install|npm\s+install|brew\s+install|yarn\s+add'; then
  echo '{"permissionDecision":"ask","permissionDecisionReason":"[確認] パッケージインストールを実行します。依存関係の変更を確認してください。"}'
  exit 0
fi

# Rule 3: File system modification via shell
if echo "$CMD" | grep -qE '\bmkdir\b|\btouch\b|\bmv\s|\bcp\s|\brm\s'; then
  echo '{"permissionDecision":"ask","permissionDecisionReason":"[確認] ファイルシステムを変更するコマンドです。実行内容を確認してください。"}'
  exit 0
fi

# Default: allow
exit 0
