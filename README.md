# Copilot Hooks Demo — ガバナンス検証リポジトリ

VS Code Copilot Chat（Agent モード）の **Hooks 機能**（v1.114）を検証するデモリポジトリです。  
AI エージェントによる開発支援において、**統制（ガバナンス）** と **効率化** を両立できるかを実証します。

## 前提条件

- VS Code 1.114 以降 + GitHub Copilot 拡張機能
- `jq` コマンドがインストール済み（`brew install jq` / `apt install jq`）

## セットアップ

```bash
git clone <this-repo>
cd copilot_demo

# スクリプトに実行権限を付与
chmod +x .github/hooks/scripts/*.sh
```

VS Code は `.github/hooks/` のフック設定を自動的に読み込みます。

## 検証シナリオ

### シナリオ 1: 保護ファイルの編集ブロック

**ファイル:** `01-block-dangerous.json`

Copilot Chat に以下を依頼してみてください：
- 「.env に API_KEY を追加して」→ `.env` ファイルの編集が deny される
- 「deploy.sh に新しい環境変数を追加して」→ デプロイ関連ファイルの編集が deny される
- 「app/main.py にエンドポイントを追加して」→ 通常ファイルは許可（通過）

### シナリオ 2: 状態変更コマンドの確認（v1.114 Ask）

**ファイル:** `02-ask-escalation.json`

Copilot Chat に以下を依頼してみてください：
- 「tests ディレクトリを作って」→ `mkdir` に対して確認が求められる
- 「この変更をコミットして」→ `git commit` に対して確認が求められる
- 「必要なパッケージをインストールして」→ `pip install` に対して確認が求められる

**v1.114 以前との違い:** 以前は deny（完全ブロック）しかできなかった操作を、ask（確認付き許可）で柔軟に制御できるようになりました。

### シナリオ 3: 監査ログの取得

**ファイル:** `03-audit-trail.json`

Copilot Chat で通常の作業をした後、監査ログを確認：

```bash
# ツール呼び出しの記録
cat .copilot-audit/pretool.jsonl | jq .

# 成功結果の記録
cat .copilot-audit/posttool.jsonl | jq .

# 生データ（診断用）
cat .copilot-audit/raw-pretool.jsonl | jq .
```

### シナリオ 4: 異常系の証跡取得（v1.114）

**ファイル:** `04-failure-handling.json`

ツール実行が失敗した場合の記録を確認：

```bash
cat .copilot-audit/failures.jsonl | jq .
```

**v1.114 以前との違い:** `postToolUse` は成功時のみ発火するようになり、失敗は専用の `postToolUseFailure` で捕捉。以前は失敗の証跡が抜け落ちる可能性がありました。

## フック構成

| ファイル | イベント | 動作 |
|---------|---------|------|
| `01-block-dangerous.json` | `preToolUse` | 保護ファイルの編集を deny |
| `02-ask-escalation.json` | `preToolUse` | 状態変更コマンドを ask（v1.114） |
| `03-audit-trail.json` | `preToolUse` + `postToolUse` | 全操作を JSONL 記録 |
| `04-failure-handling.json` | `postToolUseFailure` | 失敗を JSONL 記録（v1.114） |

## ローカルテスト

フックスクリプトは stdin に JSON を渡すことで単体テストできます：

```bash
# deny されることを確認（.env 編集）
echo '{"tool_name":"editFile","tool_input":{"file_path":".env"},"cwd":"."}' \
  | .github/hooks/scripts/block-dangerous.sh

# ask されることを確認（mkdir）
echo '{"tool_name":"runTerminalCommand","tool_input":{"command":"mkdir tests"},"cwd":"."}' \
  | .github/hooks/scripts/ask-escalation.sh
```

## 互換性

本リポジトリのフック設定は **VS Code Copilot Chat** と **Copilot CLI** の両方で動作します。  
スクリプトは両環境のフィールド名（camelCase / snake_case）を自動判定します。

## 検証レポート

詳細な検証結果は [docs/report/hooks-verification-report.md](docs/report/hooks-verification-report.md) を参照してください。
