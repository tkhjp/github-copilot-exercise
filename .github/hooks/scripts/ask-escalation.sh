#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
read_hook_input

TOOL_NAME="$(get_tool_name)"
CMD="$(get_command)"
FILE_PATH="$(get_file_path)"

# Rule A: Directory creation (VS Code uses create_directory, not shell mkdir)
# === PATTERN TEST: change this block to test different output formats ===
if [[ "$TOOL_NAME" == "create_directory" ]]; then
  emit_decision "ask" "[確認] ディレクトリを作成します。実行内容を確認してください。"
  exit 0
fi

# Rule B: File creation
if [[ "$TOOL_NAME" == "create_file" ]]; then
  emit_decision "ask" "[確認] ファイルを作成します: ${FILE_PATH##*/}。実行内容を確認してください。"
  exit 0
fi

# Rules for shell/terminal commands
case "$TOOL_NAME" in
  *terminal*|*shell*|*bash*|*command*|*Terminal*|run_in_terminal|bash|shell) ;;
  *) exit 0 ;;
esac

[[ -z "$CMD" ]] && exit 0

# Rule 1: git commit — confirm before committing
if echo "$CMD" | grep -qE 'git\s+commit'; then
  emit_decision "ask" "[確認] git commit を実行します。コミットメッセージと変更内容を確認してください。"
  exit 0
fi

# Rule 2: Package install — confirm dependency changes
if echo "$CMD" | grep -qEi 'pip\s+install|npm\s+install|brew\s+install|yarn\s+add'; then
  emit_decision "ask" "[確認] パッケージインストールを実行します。依存関係の変更を確認してください。"
  exit 0
fi

# Rule 3: File system modification via shell
if echo "$CMD" | grep -qE '\bmkdir\b|\btouch\b|\bmv\s|\bcp\s|\brm\s'; then
  emit_decision "ask" "[確認] ファイルシステムを変更するコマンドです。実行内容を確認してください。"
  exit 0
fi

# Default: allow
exit 0
