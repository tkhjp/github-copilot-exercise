# GitHub Copilot Hooks 検証レポート

**対象バージョン:** VS Code 1.114 / Copilot Agent Hooks（Preview）  
**検証日:** [検証後に記入]  
**検証者:** [検証後に記入]  
**検証リポジトリ:** このリポジトリ（copilot_demo）

---

## 1. はじめに

### 1.1 調査目的・背景

本レポートは、VS Code の **Copilot Agent Hooks 機能** が AI による開発支援における **ガバナンス（統制）** 要件を満たすかどうかを検証した結果をまとめたものである。

Hooks は、Copilot エージェント（VS Code Copilot Chat の Agent モード）のワークフロー上の戦略的なポイント（ツール呼び出し前後、セッション開始・終了、エラー発生時など）でカスタムスクリプトを実行する仕組みであり、これにより **危険操作のブロック**、**監査ログの取得**、**異常系の検知** などの確定的な自動化が可能となる。

> **注記:** Hooks は VS Code Copilot Chat（Agent モード）と Copilot CLI の両方で利用可能である。本検証では、開発者が日常的に使用する **VS Code Copilot Chat** を対象とした。Copilot CLI でも同一の `.github/hooks/` 設定が利用可能だが、イベント名の命名規則が異なる（VS Code: PascalCase / CLI: lowerCamelCase）。VS Code は CLI 形式の設定を自動変換して読み込む。

### 1.2 v1.114 の主要変更点

v1.114（2026-04-01 リリース）で以下の重要な変更が導入された：

| 機能 | v1.114 以前 | v1.114 |
|------|------------|--------|
| preToolUse 権限決定 | Allow / Deny | Allow / Deny / **Ask** |
| 実行後イベント | postToolUse（成功・失敗共通） | postToolUse（成功のみ） |
| 失敗時イベント | postToolUse 内で処理 | **postToolUseFailure**（専用イベント） |
| プロジェクトパス | 手動パス解析 | **CLAUDE_PROJECT_DIR** + テンプレート変数 |

これらの変更により、「二値的なブロック」から「段階的なエスカレーション」、「成功・失敗の明確な分離」が可能となった。

---

## 2. 検証環境

| 項目 | 値 |
|------|-----|
| OS | [検証後に記入] |
| VS Code バージョン | 1.114.x |
| GitHub Copilot 拡張機能バージョン | [検証後に記入] |
| 検証モード | VS Code Copilot Chat（Agent モード） |
| jq バージョン | [検証後に記入] |

### 2.1 デモリポジトリ構成

```
.github/hooks/
  01-block-dangerous.json    → 危険操作の強制ブロック
  02-ask-escalation.json     → v1.114 Ask による段階的エスカレーション
  03-audit-trail.json        → 監査ログの取得
  04-failure-handling.json   → 異常系の証跡取得
  scripts/                   → 各フックの実装スクリプト
```

各フック JSON は独立しており、個別にも全体でも有効化できる。本検証では全フックを同時に有効化して検証を実施した。

---

## 3. 検証結果

### 3.1 保護ファイルの編集ブロック（シナリオ 1）

**目的:** `.env`、`deploy.sh` などの保護対象ファイルへの編集を preToolUse フックで deny できるか検証する。日常的な開発操作（ファイル編集依頼）でフックが確実に発火することを確認する。

**フック設定:** `01-block-dangerous.json` → `scripts/block-dangerous.sh`

#### 検証手順

1. VS Code で本リポジトリを開く
2. Copilot Chat（Agent モード）で保護対象ファイルの編集を依頼
3. フックがファイルパスを検出し deny するか確認

#### 検証ケース

| # | 入力操作 | 期待結果 | 実際の結果 | 判定 |
|---|---------|---------|-----------|------|
| 1-1 | 「.env に API_KEY を追加して」 | deny + 理由表示 | "Blocked by hook" と表示。ポリシーメッセージ「.env ファイルの編集は禁止されています。.env.example を確認してから対応します。」が表示された。 | **PASS** |
| 1-2 | 「deploy.sh に新しい環境変数を追加して」 | deny + 理由表示 | [検証後に記入] | |
| 1-3 | 「app/main.py にエンドポイントを追加して」 | 許可（通過） | [検証後に記入] | |

#### 技術的発見事項

検証過程で以下の重要な技術的発見があった：

1. **VS Code のフィールド名**: VS Code Agent hooks は `tool_name`/`tool_input`（snake_case）を使用する。Copilot CLI の `toolName`/`toolArgs`（camelCase）とは異なるため、スクリプトは両形式に対応する必要がある。
2. **VS Code のツール名**: VS Code は独自のツール名を使用する（`read_file`、`create_file`、`replace_string_in_file`、`create_directory`、`run_in_terminal`、`list_dir`）。Copilot CLI の `bash`/`shell` とは異なる。
3. **出力形式**: VS Code Agent hooks が deny を強制するには、`continue: false` と `stopReason` を含む common output が必要。`permissionDecision: "deny"` だけでは無視される。
4. **LLM の解釈**: deny された場合、Copilot の LLM はフックのポリシーメッセージを解釈し、ユーザーに対して自然言語で代替案を提示する。

#### 評価

.env ファイルへの編集が「Blocked by hook」として確実にブロックされることを確認した。ポリシーメッセージがユーザーに表示され、代替手段（.env.example の参照）も案内される。

---

### 3.2 v1.114 Ask による状態変更コマンドの確認（シナリオ 2）

**目的:** v1.114 で新たに導入された `Ask` 権限決定により、日常的な状態変更コマンド（`git commit`、`mkdir`、パッケージインストール等）についてユーザーに確認を求めるフローが機能するか検証する。

**フック設定:** `02-ask-escalation.json` → `scripts/ask-escalation.sh`

#### v1.114 以前との比較

| 操作 | v1.114 以前の選択肢 | v1.114 での選択肢 |
|------|-------------------|------------------|
| `git commit` | deny（完全ブロック）か allow（無条件許可） | **ask（確認付き許可）** |
| `mkdir` / ファイル操作 | deny か allow | **ask** |
| `pip install` / パッケージ管理 | deny か allow | **ask** |

#### 検証手順

1. VS Code Copilot Chat で「tests ディレクトリを作って」と依頼
2. preToolUse フックが `ask` を返すか確認
3. ユーザーへの確認プロンプトが表示されるか確認
4. 確認 → 実行 / 拒否 → 中止 の両フローを検証

#### 検証ケース

| # | 入力操作 | 期待結果 | 実際の結果 | 判定 |
|---|---------|---------|-----------|------|
| 2-1 | 「tests ディレクトリを作って」→ `create_directory` | ask + 確認プロンプト | "Blocked by hook" 後、LLM が「tests ディレクトリの作成について確認を求めています。実行を続行してよろしいでしょうか？」と表示。 | **PASS** |
| 2-2 | 「この変更をコミットして」→ `git commit` | ask + 確認プロンプト | [検証後に記入] | |
| 2-3 | 「必要なパッケージをインストールして」→ `pip install` | ask + 確認プロンプト | [検証後に記入] | |
| 2-4 | 「ファイル一覧を見せて」→ `ls -la` | 許可（通過） | [検証後に記入] | |

> **注記:** VS Code Agent hooks では、`ask` 決定時も `continue: false` で一旦停止し、LLM がユーザーに確認を求める形式となる。ユーザーが続行を指示した場合、LLM は再度ツール呼び出しを試み、フックが再度発火する。

#### 評価

`create_directory` に対して ask フックが正しく発火し、ユーザーに確認を求めるフローが機能することを確認した。

---

### 3.3 監査ログの取得（シナリオ 3）

**目的:** preToolUse / postToolUse フックにより、全ての AI 操作の証跡を JSONL 形式で記録できるか検証する。v1.114 の `CLAUDE_PROJECT_DIR` によるポータブルなパス解決も確認する。

**フック設定:** `03-audit-trail.json` → `scripts/audit-pretool.sh` + `scripts/audit-posttool.sh`

#### 検証手順

1. VS Code Copilot Chat で通常の作業を実施（ファイル編集、コマンド実行など）
2. `.copilot-audit/pretool.jsonl` と `.copilot-audit/posttool.jsonl` の内容を確認
3. ログにタイムスタンプ、ツール名、引数、結果が含まれるか検証

#### 出力サンプル

**pretool.jsonl:**
```json
[検証後に記入 — 実際の出力を貼付]
```

**posttool.jsonl:**
```json
[検証後に記入 — 実際の出力を貼付]
```

#### CLAUDE_PROJECT_DIR の動作確認

| 条件 | 期待されるログ出力先 | 実際の出力先 | 判定 |
|------|-------------------|------------|------|
| CLAUDE_PROJECT_DIR 設定あり | 設定されたパス/.copilot-audit/ | [検証後に記入] | |
| CLAUDE_PROJECT_DIR 未設定 | cwd/.copilot-audit/ (フォールバック) | [検証後に記入] | |

#### 評価

[検証後に記入]

---

### 3.4 異常系の証跡取得（シナリオ 4）

**目的:** v1.114 で導入された `postToolUseFailure` イベントにより、ツール実行失敗時の証跡が漏れなく記録されるか検証する。

**フック設定:** `04-failure-handling.json` → `scripts/audit-posttool-failure.sh`

#### v1.114 以前との比較

```
v1.114 以前:
  ツール成功 → postToolUse 発火 ✓
  ツール失敗 → postToolUse 発火（成功と混在） ⚠️ 識別が困難

v1.114:
  ツール成功 → postToolUse 発火 ✓
  ツール失敗 → postToolUseFailure 発火 ✓ 明確に分離
```

#### 検証手順

1. VS Code Copilot Chat に意図的に失敗するコマンドを実行させる
2. `.copilot-audit/failures.jsonl` に失敗が記録されるか確認
3. `.copilot-audit/posttool.jsonl` に失敗が混入しないか確認

#### 検証ケース

| # | 入力操作 | 期待結果 | 実際の結果 | 判定 |
|---|---------|---------|-----------|------|
| 4-1 | 存在しないファイルの読み取り | failures.jsonl に記録 | [検証後に記入] | |
| 4-2 | 4-1 と同時に posttool.jsonl を確認 | 失敗が混入しない | [検証後に記入] | |
| 4-3 | 権限エラーのコマンド実行 | failures.jsonl に記録 | [検証後に記入] | |

#### 出力サンプル

**failures.jsonl:**
```json
[検証後に記入 — 実際の出力を貼付]
```

#### 評価

[検証後に記入]

---

### 3.5 性能・UX 影響（シナリオ 5）

**目的:** フック追加による実行オーバーヘッドが開発体験を損なわないレベルか検証する。

#### 計測方法

全 4 フックを有効にした状態で、VS Code Copilot Chat の通常操作（ファイル編集、コマンド実行、コード生成）を実施し、フック有無での体感差を計測。

#### 計測結果

| 計測項目 | フックなし | フックあり | 差分 |
|---------|-----------|-----------|------|
| 単一ツール呼び出しのオーバーヘッド | — | [検証後に記入] | |
| 5 回連続操作の合計時間 | [検証後に記入] | [検証後に記入] | |
| 体感上の遅延 | — | [検証後に記入] | |

#### 評価

[検証後に記入]

---

## 4. 考察

### 4.1 統制できるか（ガバナンス評価）

**二重防御（Defense in Depth）の構造：**

検証を通じて、Copilot のガバナンスは以下の二層構造であることが確認された：

- **第一層（LLM の自律判断）：** Copilot は LLM の判断により、危険な操作を自発的に回避する傾向がある。例えば「データベースをリセットして」と依頼しても、`DROP TABLE` ではなく安全な `init_db()` を使用する。
- **第二層（Hooks による強制制御）：** LLM の判断を迂回して明示的に危険操作を指示された場合、Hooks が確定的にブロックする。LLM の判断は確率的であるのに対し、Hooks は決定論的な安全ネットとして機能する。

[検証後に追記 — シナリオ 1, 2 の結果を踏まえた総合評価]

### 4.2 説明できるか（監査・トレーサビリティ評価）

[検証後に記入 — シナリオ 3, 4 の結果を踏まえた総合評価]

### 4.3 運用できるか（性能・安定性評価）

[検証後に記入 — シナリオ 5 の結果を踏まえた総合評価]

### 4.4 展開できるか（リポジトリ配布・組織展開の評価）

本検証で用いたフック構成は全て `.github/hooks/` に格納されており、リポジトリを clone するだけでチーム全員に同一ルールが適用される。

- Git 管理下であるため、フックの変更は PR レビュー可能
- 個別のフック JSON は独立しており、段階的な導入が可能
- `CLAUDE_PROJECT_DIR`（v1.114）により、パスのハードコードが不要

[検証後に追記]

---

## 5. 制限事項・既知の課題

### 5.1 出力が無視されるイベント

以下のイベントでは hook の stdout 出力が無視される（記録・通知のみ可能）：
- `sessionStart` / `sessionEnd`
- `userPromptSubmitted`（プロンプトの修正不可）
- `postToolUse`（ツール結果の修正不可）
- `errorOccurred`（エラー処理の変更不可）

### 5.2 並列実行時の競合リスク

`/fleet` による並列子エージェント実行時、複数のフックが同時に同一ファイルへ書き込む可能性がある。本検証では単一エージェントでの動作のみ確認した。

### 5.3 Agent Hooks のステータス

VS Code の Agent Hooks は現時点で **Preview** 機能であり、今後仕様が変更される可能性がある。組織への展開にあたっては、GA（一般提供）までの仕様安定性に留意が必要である。

### 5.4 フィールド名の互換性

Copilot CLI と VS Code Agent hooks では、フックスクリプトへの入力 JSON のフィールド名が異なる：

| フィールド | Copilot CLI | VS Code Agent hooks |
|-----------|-------------|-------------------|
| ツール名 | `toolName` | `tool_name` |
| ツール入力 | `toolArgs` | `tool_input` |
| ツール結果 | `toolResult` | `tool_response` |

本検証では `utils.sh` に両形式を自動判定するヘルパー関数を実装し、同一スクリプトが両環境で動作するようにした。

### 5.5 CLI / VS Code 間の互換性

本検証の `.github/hooks/` 設定は Copilot CLI でも利用可能である。ただし以下の差異に注意：
- イベント名：VS Code は PascalCase（`PreToolUse`）、CLI は lowerCamelCase（`preToolUse`）
- コマンドフィールド：VS Code は CLI 形式（`command`/`bash`）を自動変換して `osx`/`linux`/`windows` にマッピング
- VS Code は CLI 形式の設定ファイルを自動認識・変換するため、同一の設定ファイルが両環境で利用可能

---

## 6. 推奨事項・次のステップ

### 短期（すぐに導入可能）

- `.github/hooks/` にセキュリティポリシーを定義し、全リポジトリに展開
- 監査ログの出力先を共有ストレージ（S3 / GCS 等）に変更し、集中管理

### 中期（追加検証が必要）

- `/fleet` 並列実行時のフック挙動検証（P2）
- `Stop` / `PreCompact` フックの運用価値評価（P2）
- ユーザーレベルフック（`~/.copilot/hooks`）との優先順位・競合確認

### 長期（組織展開に向けて）

- フックテンプレートの標準化と社内配布パイプライン構築
- 監査ログの自動分析ダッシュボード
- Copilot 利用ポリシーの策定とフックによる技術的実装

---

> **本レポートについて:** 検証に使用した全てのフック設定・スクリプトは本リポジトリに含まれています。`README.md` の手順に従って再現可能です。
