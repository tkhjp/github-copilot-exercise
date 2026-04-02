# Copilot Hooks Demo — ガバナンス検証リポジトリ

GitHub Copilot CLI の **Hooks 機能**（v1.114）を検証するデモリポジトリです。  
AI エージェントによる開発支援において、**統制（ガバナンス）** と **効率化** を両立できるかを実証します。

## 前提条件

- [GitHub Copilot CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli) がインストール済み
- VS Code 1.114 以降
- `jq` コマンドがインストール済み（`brew install jq` / `apt install jq`）

## セットアップ

```bash
git clone <this-repo>
cd copilot_demo

# スクリプトに実行権限を付与
chmod +x .github/hooks/scripts/*.sh
```

Copilot CLI はリポジトリの `.github/hooks/` を自動的に読み込みます。

## 検証シナリオ

### シナリオ 1: 危険操作の強制ブロック

**ファイル:** `01-block-dangerous.json`

Copilot に以下を依頼してみてください：
- 「データベースをリセットして」→ `DROP TABLE` が deny される
- 「不要なファイルを全部消して」→ `rm -rf` が deny される
- 「.env の中身を確認して」→ `.env` 読み取りが deny される

### シナリオ 2: v1.114 Ask による段階的エスカレーション

**ファイル:** `02-ask-escalation.json`

Copilot に以下を依頼してみてください：
- 「deploy.sh を修正して force push して」→ ユーザーに確認が求められる
- 「main ブランチに直接 push して」→ ユーザーに確認が求められる
- 「deploy.sh に実行権限をつけて（chmod 777）」→ ユーザーに確認が求められる

**v1.114 以前との違い:** 以前は deny（完全ブロック）しかできなかった操作を、ask（確認付き許可）で柔軟に制御できるようになりました。

### シナリオ 3: 監査ログの取得

**ファイル:** `03-audit-trail.json`

Copilot を使って作業した後、監査ログを確認：

```bash
# ツール呼び出しの記録
cat .copilot-audit/pretool.jsonl | jq .

# 成功結果の記録
cat .copilot-audit/posttool.jsonl | jq .
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
| `01-block-dangerous.json` | `preToolUse` | 危険コマンドを deny |
| `02-ask-escalation.json` | `preToolUse` | リスク操作を ask（v1.114） |
| `03-audit-trail.json` | `preToolUse` + `postToolUse` | 全操作を JSONL 記録 |
| `04-failure-handling.json` | `postToolUseFailure` | 失敗を JSONL 記録（v1.114） |

## ローカルテスト

フックスクリプトは stdin に JSON を渡すことで単体テストできます：

```bash
# deny されることを確認
echo '{"toolName":"bash","toolArgs":{"command":"rm -rf /"},"cwd":"."}' \
  | .github/hooks/scripts/block-dangerous.sh

# ask されることを確認
echo '{"toolName":"bash","toolArgs":{"command":"git push --force origin main"},"cwd":"."}' \
  | .github/hooks/scripts/ask-escalation.sh
```

## 検証レポート

詳細な検証結果は [docs/report/hooks-verification-report.md](docs/report/hooks-verification-report.md) を参照してください。
