# Microsoft Copilot 判断テスト — PNG vs PPT vs Word 実行手順

Phase 4 judgment テスト (`tc02_judge` / `tc03_judge`) を Microsoft Copilot Web 版に対し、
**同一内容を 3 種のフォーマット (PNG / PPTX / DOCX) で入力**し、
判断品質がフォーマットによって変わるかを計測する実験の実行手順。

## 全体フロー

```
[1] 素材生成 (自動)          [3] 採点 UI 起動 (自動)
      │                             │
      ▼                             ▼
 inputs/*.pptx                human_eval.html  ──┐
 inputs/*.docx                      ▲           │
 images/*.png (既存)                │           │
      │                       [4] 人手採点       │
      │                             │           │
 [2] Copilot Web に            [5] JSON Export   │
     手動アップロード + 貼付         │           │
      │                             ▼           │
      ▼                       human_scores.json  │
 description.md × 6                  │           │
      ──────────────────────────────┘           │
                                [6] レポート生成 ◀──┘
                                      │
                                      ▼
                               copilot_report.md
```

## ステップ 1 — 素材生成

```bash
python tests/text_vs_image/generate_test_pptx.py
python tests/text_vs_image/generate_test_docx.py
```

以下 4 ファイルが `tests/text_vs_image/inputs/` に作られる:

- `02_ui_change.pptx` / `03_complex_arch.pptx` — PPT 版、`python-pptx` で元 PNG を 1:1 近い shape レイアウトに再構成
- `02_ui_change.docx` / `03_complex_arch.docx` — Word 版、タイトル + 質問 + 同じ PNG を埋め込み

## ステップ 2 — Copilot Web で回答を取得

`test_cases.yaml` の `tc02_judge` / `tc03_judge` の `question` フィールドをそのままコピーし、
対応する入力ファイルを Copilot Web (<https://copilot.microsoft.com/>) にアップロード、回答を得る。

各回答を下記 6 ファイルに貼り付ける (既に雛形あり):

| quant | ファイル | 入力 |
| --- | --- | --- |
| copilot_png  | `benchmarks/out/phase4/quality/copilot_png_tc02_judge_description.md` | `images/02_ui_change.png` |
| copilot_png  | `benchmarks/out/phase4/quality/copilot_png_tc03_judge_description.md` | `images/03_complex_arch.png` |
| copilot_pptx | `benchmarks/out/phase4/quality/copilot_pptx_tc02_judge_description.md` | `inputs/02_ui_change.pptx` |
| copilot_pptx | `benchmarks/out/phase4/quality/copilot_pptx_tc03_judge_description.md` | `inputs/03_complex_arch.pptx` |
| copilot_docx | `benchmarks/out/phase4/quality/copilot_docx_tc02_judge_description.md` | `inputs/02_ui_change.docx` |
| copilot_docx | `benchmarks/out/phase4/quality/copilot_docx_tc03_judge_description.md` | `inputs/03_complex_arch.docx` |

各ファイルは `## Output` 行より前にテンプレート、以降に Copilot の回答を貼り付ける。
`## Output` の下の HTML コメントは削除しても残しても良い (採点 UI は `## Output` 以降のみ表示)。

**YYYY-MM-DD** 部分は手動で実施日に置き換える (再現性のためのメタデータ、必須ではない)。

## ステップ 3 — 採点 UI を再生成

```bash
python tests/text_vs_image/generate_human_eval_ui.py \
    --extra-quants copilot_png,copilot_pptx,copilot_docx
open tests/text_vs_image/human_eval.html
```

quant ドロップダウンに 7 個 (q4 / q5 / q8 / e2b / copilot_png / copilot_pptx / copilot_docx) が並ぶ。
copilot_* に切り替えると、中央の "Model Output" パネルにステップ 2 で貼り付けた Copilot の回答が表示される。
右パネルで各 reasoning point に `1.0 / 0.5 / 0.0` (present / partial / missing) を付与。
LLM judgement 列は Copilot には存在しないため "— n/a" と表示される (想定どおり)。

スコアは `localStorage` に自動保存される。

## ステップ 4 — JSON Export

`human_eval.html` フッターの **Export JSON** ボタンを押し、`human_scores.json` をダウンロード。
通常は `~/Downloads/human_scores.json` に保存される。

## ステップ 5 — 取り込み (任意)

ローカル LLM の `_summary.json` と同様の `_human_summary.json` を作るなら:

```bash
python tests/text_vs_image/import_human_scores.py \
    --scores-json ~/Downloads/human_scores.json
```

judgment ケースの `reasoning_points` フィールドに対応済み (以前は `ground_truth_facts` のみだった)。

## ステップ 6 — 日本語レポート生成

```bash
python tests/text_vs_image/generate_copilot_report.py \
    --human-scores ~/Downloads/human_scores.json \
    --out tests/text_vs_image/copilot_report.md
```

`copilot_report.md` に、

- 実験概要 (目的・対象・採点方式・n_runs の非対称性注記)
- 評価対象 quant 一覧
- ケース別スコアサマリー (7 quants × 2 ケース)
- tc03_judge の reasoning point 別 verdict (視覚依存項 j07/j08/j09 のフォーマット間挙動)
- 考察テンプレート (PNG/PPTX/DOCX 差分の解釈観点)

が日本語で出力される。

## カスタマイズ

- **quant を絞る**: `--quants q8,copilot_png,copilot_pptx,copilot_docx` (例えば local LLM の最良のみと比較)
- **ケースを絞る**: `--tcs tc02_judge` (単一ケースに集中)
- **採点済み件数 < 全件数** の部分採点でも `n/a` にならず `0.XXX (k/N)` 表記で平均が出る

## 既知の注意点

- **tc03_judge の j07 / j08 / j09 は線色と凡例色に依存する。** Word (DOCX) では PNG 埋込のみのため、Copilot が画像を実際に解釈できた場合のみ `present` が期待される。全 `missing` なら「DOCX 添付の画像が Copilot の視覚パイプラインに届いていない」ことを示唆する、想定される研究シグナル。
- **Copilot は 1 回のみの回答** (n_runs=1)。ローカル LLM は n_runs=3 の多数決なので、数値を横並びにする際は Copilot のばらつきを考慮すること。
- **Copilot Web が PPTX/DOCX をそもそも受け付けない場合**: Edge サイドバー版、Copilot for Microsoft 365 (Business/Enterprise)、または Copilot Studio などの代替を検討。ステップ 2 の最初の 1 ケースで早期発見を。
