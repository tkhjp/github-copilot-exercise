# Image Describer PoC 検証ガイド

**目的**: Copilot Chat が画像アップロード機能を使えない環境でも、外部 Vision LLM（Gemini）経由で画像内容を理解できるかを検証する。MCP も VS Code 拡張機能も使わず、**`.github/copilot-instructions.md`** と **`run_in_terminal` 組み込みツール** と **プレーンな Python CLI スクリプト** だけで実現する。

## アーキテクチャまとめ

```
ユーザー発話 (.pptx パスを含む)
   ↓
Copilot Chat (agent mode) が .github/copilot-instructions.md を読み込む
   ↓
命令に従い run_in_terminal ツールで:
   python tools/describe_pptx.py samples/sample.pptx
   ↓
Default Approvals ダイアログ → ユーザー承認
   ↓
スクリプトが python-pptx で画像抽出 → Gemini Vision に送信 → Markdown を stdout 出力
   ↓
Copilot Chat がその Markdown を読み取り、ユーザーの質問に回答
```

**使用した Copilot Chat 機構**:
1. カスタム命令: [.github/copilot-instructions.md](../../.github/copilot-instructions.md)
2. プロンプトファイル（スラッシュコマンド）: [.github/prompts/describe-image.prompt.md](../../.github/prompts/describe-image.prompt.md)、[.github/prompts/describe-pptx.prompt.md](../../.github/prompts/describe-pptx.prompt.md)
3. 組み込み `run_in_terminal` ツール（Copilot Chat 本体機能）

## 依存セットアップ（一度だけ）

```bash
# pyenv 3.13.2 を有効化
eval "$(pyenv init --path)" && eval "$(pyenv init -)"
# 追加パッケージ（google-genai, dotenv, Pillow は既存環境に入っている）
pip install python-pptx python-docx
```

`.env` に `GEMINI_API_KEY` が設定済であることを確認（本プロジェクトでは設定済）。
必要なら `GEMINI_MODEL=gemini-2.5-flash` （または `gemini-2.5-pro` / `gemini-3.1-pro-preview` など）を `.env` または環境変数で指定。

## Step A: スクリプト単体動作確認（Copilot Chat 不要）

検証前にスクリプト自体が動くことを確認する。以下を順に実行し、いずれも exit code 0 で Markdown が stdout に出力されれば成功。

```bash
cd /Volumes/mac_hd/work/jeis/copilot_demo

# サンプルファイル生成（一度だけ）
python samples/generate_samples.py

# 単体画像
python tools/describe_image.py samples/diagram.png

# pptx（全スライド）
python tools/describe_pptx.py samples/sample.pptx

# pptx（スライド 3 のみ）
python tools/describe_pptx.py samples/sample.pptx --slide 3

# docx
python tools/describe_docx.py samples/sample.docx
```

**確認済み出力例** (describe_image.py samples/diagram.png):

```markdown
# samples/diagram.png の記述
- mime: `image/png`
- model: `gemini-3.1-pro-preview`

### 1. テキスト内容（OCR）
*   **上部タイトル:** Order Processing Flow
*   **左のボックス内:** Receive Order
*   **中央のボックス内:** Validate Payment
*   **右のボックス内:** Ship Product
*   **左下部のテキスト:** Success rate: 97.3% (Q1 2026)

### 2. 図表・ダイアグラムの構造
左から右へ進行する 3 ステップの直線的なフローチャート ...

### 3. 色とレイアウト
薄い青・薄い黄色・薄い緑の 3 色分けされたボックス ...
```

**セキュリティ動作確認**:
```bash
python tools/describe_image.py samples/nope.png      # → exit 2, File not found
python tools/describe_image.py ../../etc/hosts       # → exit 2, Path escapes workspace root
python tools/describe_image.py README.md             # → exit 3, unsupported extension '.md'
```

## Step B: Copilot Chat での検証

### 準備

1. VS Code を再起動（`.github/copilot-instructions.md` を読ませるため）
2. Copilot Chat を開き、モードを **Agent** に切り替え
3. Chat 画面上部の Referenced context 表示で `copilot-instructions.md` が認識されていることを確認

### Scenario A — pptx 自動トリガー

Chat に入力:
```
samples/sample.pptx の各スライドの内容を説明してください
```

**期待動作**:
- Copilot が `run_in_terminal` ツールを選択
- 実行しようとするコマンド: `python tools/describe_pptx.py samples/sample.pptx`
- Default Approvals ダイアログ表示 → Allow をクリック
- Copilot がスクリプトの stdout を受け取り、スライドごとの画像内容を日本語で要約

**成功判定**:
- Copilot の回答に「Order Processing Flow」「Monthly Revenue」など、実際の画像内テキストが含まれる
- 推測ではなく画像から直接読み取った内容が反映されている

### Scenario B — 単体画像自動トリガー

Chat に入力:
```
samples/diagram.png は何を示していますか？
```

**期待動作**:
- Copilot が `python tools/describe_image.py samples/diagram.png` を `run_in_terminal` で実行
- Default Approvals ダイアログ → Allow
- フローチャートの構造・3つのノード・成功率などを回答

### Scenario C — 手動スラッシュコマンド（最も確実なフォールバック）

Chat に入力:
```
/describe-image samples/diagram.png
```

**期待動作**:
- `.github/prompts/describe-image.prompt.md` が発火
- プロンプトの指示通り `python tools/describe_image.py samples/diagram.png` を実行
- 結果を日本語で要約

pptx 版:
```
/describe-pptx samples/sample.pptx
```

### Scenario D — カスタム命令の強さの確認

もし Scenario A/B で Copilot がスクリプトを呼ばずに推測で答えようとした場合、以下を追記して再試行:
```
.github/copilot-instructions.md のルールに従い、画像記述スクリプトを先に実行してください
```

これは「自動トリガーがLLMバイアス依存」という既知の限界を回避するプロンプトパターン。

## 記録すべきエビデンス

- [ ] Scenario A スクリーンショット（チャット入力 + Default Approvals ダイアログ + 最終回答）
- [ ] Scenario B スクリーンショット（同上）
- [ ] Scenario C スクリーンショット（/describe-image 発火）
- [ ] `run_in_terminal` 実行ログ（Terminal パネル）
- [ ] Default Approvals ダイアログで「Allow once」を選んでいるスクリーンショット
- [ ] Copilot Chat の Referenced context に `copilot-instructions.md` が表示されている確認

## 成功判定基準

| 項目 | 基準 |
|---|---|
| スクリプト単体動作 | 4つのコマンドすべてが exit 0 で Markdown を出力 |
| Scenario A (pptx自動) | Copilot がスクリプトを実行し、画像内テキストが回答に現れる |
| Scenario B (画像自動) | 同上 |
| Scenario C (スラッシュ) | プロンプトファイルが発火しスクリプトが実行される |
| Default Approvals | Bypass されず、各ツール呼び出しで承認ダイアログが出る |
| MCP 不使用 | `.vscode/mcp.json` や MCP サーバーは一切使っていない |
| 拡張機能 不使用 | カスタム VS Code 拡張は一切インストールしていない |

## 制約事項・既知の限界（レポート本体に必ず記載）

1. **「自動」トリガーはLLMバイアス依存**
   - カスタム命令で強く指示しても、Copilot Chat が毎回必ずスクリプトを呼ぶ保証はない。
   - Agent mode + 明確な命令で実用上十分だが、確実性を求める場合は **手動スラッシュコマンド**（`/describe-image`、`/describe-pptx`）が最も信頼できる。

2. **`run_in_terminal` が禁止されている環境では実現不可**
   - MCP に加えて組み込みターミナルツールまで無効化されている場合、本方式は動作しない。
   - その場合の代替案: ユーザーがチャット外で `python tools/describe_image.py` を手動実行し、stdout をコピーしてチャットに貼り付ける。これは「SKILL / RULE」とは呼べないが、機能面は代替可能。

3. **Default Approvals の承認疲れ**
   - 1 つの pptx 処理は 1 回の `run_in_terminal` 呼び出しなので承認は 1 回。
   - ただし、複数ファイルを連続処理する場合は承認クリックが増える。JEIS ポリシーで Bypass/Autopilot は禁止なので受け入れる。

4. **クリップボード貼付画像は非対応**
   - ファイルパスがないとスクリプトを起動できない。ユーザーが画像を扱う場合は一旦ワークスペース内に保存する必要がある。
   - クリップボード連携には VS Code 拡張機能が必要で、本 PoC のスコープ外。

5. **pptx の SmartArt/グラフは非対応**
   - 初版では `MSO_SHAPE_TYPE.PICTURE` のみ対応（埋め込まれた画像として記録されているもの）。
   - PowerPoint のネイティブ SmartArt やチャート（XML 定義）はスキップされる。将来拡張で対応可能。

6. **思考モデルの出力揺れ**
   - `gemini-3.x-pro-preview` 系など thinking mode のモデルは、まれに思考テキストを answer 部に混入させる。
   - `tools/lib/gemini_client.py` の `_extract_answer_text()` で `part.thought == True` を除外しているが、100% 除去ではない。
   - 安定性を優先するなら `GEMINI_MODEL=gemini-2.5-flash` を推奨。

## 関連ファイル

| ファイル | 役割 |
|---|---|
| [.github/copilot-instructions.md](../../.github/copilot-instructions.md) | Copilot への画像処理ルール（命令レイヤー） |
| [.github/prompts/describe-image.prompt.md](../../.github/prompts/describe-image.prompt.md) | `/describe-image` スラッシュコマンド |
| [.github/prompts/describe-pptx.prompt.md](../../.github/prompts/describe-pptx.prompt.md) | `/describe-pptx` スラッシュコマンド |
| [tools/describe_image.py](../../tools/describe_image.py) | 単体画像 CLI |
| [tools/describe_pptx.py](../../tools/describe_pptx.py) | pptx CLI |
| [tools/describe_docx.py](../../tools/describe_docx.py) | docx CLI |
| [tools/lib/gemini_client.py](../../tools/lib/gemini_client.py) | Gemini Vision ラッパー |
| [tools/lib/pptx_extractor.py](../../tools/lib/pptx_extractor.py) | pptx の Picture シェイプ抽出 |
| [tools/lib/docx_extractor.py](../../tools/lib/docx_extractor.py) | docx の image part 抽出 |
| [tools/lib/safe_path.py](../../tools/lib/safe_path.py) | ワークスペース外への traversal 防止 |
| [samples/generate_samples.py](../../samples/generate_samples.py) | 検証用サンプル生成 |
