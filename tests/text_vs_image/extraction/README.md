# Copilot 抽出プロンプト実験

お客様が Copilot Chat に画像 / PPT を渡して verbatim なテキスト抽出をさせるための
**フォーマット別プロンプト**を開発・評価するための実験基盤。

- 設計書: [docs/superpowers/specs/2026-04-24-copilot-extraction-prompt-design.md](../../../docs/superpowers/specs/2026-04-24-copilot-extraction-prompt-design.md)
- 先行実験: [../COPILOT_FINDINGS.md](../COPILOT_FINDINGS.md)

## 1. 材料生成 (1 回だけ)

```bash
python tests/text_vs_image/extraction/generate_extraction.py
```

これで以下が生成される:

- `extraction_test.pptx` — 8 slides (P1-P8) 入り、Copilot にアップロードする本体
- `p01_ui_callouts.png` 〜 `p08_org_chart.png` — 各 slide に対応する独立 PNG (8 枚)
- `ground_truth.yaml` — 採点時に Gemini judge が参照する正解事実リスト

## 2. プロンプト試行 (何回でも)

### 2.1 試行用の prompt_id を決める

例: `pptx_detailed_v1` / `png_cot_v2` など。内容が分かる任意の文字列。

### 2.2 Copilot Web で試行

1. <https://copilot.microsoft.com/> を開く
2. **PPTX 試行**: `extraction_test.pptx` をアップロード → プロンプトを貼付 → 送信 → 回答をコピー → 下記ファイルに保存
   - `benchmarks/out/extraction/{prompt_id}/pptx_response.md`
3. **PNG 試行 (8 回)**: `p01_ui_callouts.png` 〜 `p08_org_chart.png` を 1 枚ずつアップロード → 同じプロンプトを貼付 → 回答を
   - `benchmarks/out/extraction/{prompt_id}/png_p01_response.md` 〜 `png_p08_response.md` に保存
4. (任意) 使用したプロンプト全文を
   - `benchmarks/out/extraction/{prompt_id}/prompt.md` に保存しておくと後で比較しやすい

各 response MD は `## Output` 以下に回答を貼り付けるだけで可 (`## Output` ヘッダーは必須):

```markdown
# {prompt_id} / png_p01

**Date:** 2026-04-25

## Output

<Copilot の回答をここに貼り付け>
```

### 2.3 採点

```bash
python tests/text_vs_image/extraction/judge_extraction.py \
    --prompt-id {prompt_id}
```

Gemini 2.5 Flash が recall (n_runs=3) と hallucination (各 1 run) を判定し、
`benchmarks/out/extraction/{prompt_id}/scores/` に以下を書き出す:

- `png_p01_scores.json` 〜 `png_p08_scores.json` — 各パターンごとの採点
- `pptx_scores.json` — PPTX 応答を per-slide 分離して採点したリスト
- `summary.json` — 試行メタ情報

ターミナルには per-slide の recall と hallucination 件数が表示される。

## 3. 比較レポート (複数 prompt_id 試した後)

```bash
python tests/text_vs_image/extraction/extraction_report.py
```

`extraction_report.md` に以下を含む日本語レポートが生成される:

- プロンプト × フォーマットの recall 平均 / ハルシネーション合計
- パターン別 recall (PNG 表 / PPTX 表)
- パターン別ハルシネーション合計
- ハルシネーション具体例 (プロンプトごとに先頭 3 件)

## 4. トラブルシュート

### Copilot が PPTX の途中 slide で応答を切る

`pptx_response.md` をそのまま保存 (完全でなくて OK)。`judge_extraction.py` の
per-slide 分割ロジックは欠落 slide を空として扱い、該当 slide の recall は 0 になる。

**対策**: slide 数を減らして複数試行に分ける / CoT 系プロンプトで "最後の slide
まで書いてください" と明示する など、プロンプト工夫の検証対象になる。

### `## Slide N` 見出しが無くて per-slide 分割できない

現状の分割は `## Slide N` / `## スライド N` の見出しに依存。プロンプトに
"各スライドは `## Slide N` の見出しで始めてください" と書くと確実。
見出しなしの応答は slide 1 として扱われ、slide 2-8 は空になる (recall=0)。

### `GEMINI_API_KEY not set`

リポジトリ直下の `.env` に `GEMINI_API_KEY=...` を追加すること。
`.env` は `.gitignore` に登録済みなのでコミットされない。
