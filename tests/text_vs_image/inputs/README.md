# Copilot 実験 — アップロード素材一式

Microsoft Copilot Web (<https://copilot.microsoft.com/>) で 6 回の試行を行うために必要なファイル群。

## このフォルダの中身

| ファイル | 用途 |
| --- | --- |
| `02_ui_change.png`   | tc02_judge — PNG 入力 (`copilot_png`) |
| `02_ui_change.pptx`  | tc02_judge — PPTX 入力 (`copilot_pptx`) |
| `02_ui_change.docx`  | tc02_judge — DOCX 入力 (`copilot_docx`) |
| `03_complex_arch.png`  | tc03_judge — PNG 入力 |
| `03_complex_arch.pptx` | tc03_judge — PPTX 入力 |
| `03_complex_arch.docx` | tc03_judge — DOCX 入力 |
| `tc02_judge_question.txt` | tc02_judge 用の質問文 (コピペ用) |
| `tc03_judge_question.txt` | tc03_judge 用の質問文 (コピペ用) |

## 6 回の試行 — 手順

1. Copilot Web を開く
2. 下記テーブルの **アップロードファイル** を添付
3. 対応する **質問文ファイル** の中身をコピーし、Copilot のチャット欄に貼り付けて送信
4. 返ってきた回答を全選択・コピーし、**保存先** のファイルの `## Output` 行以下に貼り付ける

| # | アップロードファイル | 質問文 | 保存先 |
| --- | --- | --- | --- |
| 1 | `02_ui_change.png`   | `tc02_judge_question.txt` | `benchmarks/out/phase4/quality/copilot_png_tc02_judge_description.md` |
| 2 | `02_ui_change.pptx`  | `tc02_judge_question.txt` | `benchmarks/out/phase4/quality/copilot_pptx_tc02_judge_description.md` |
| 3 | `02_ui_change.docx`  | `tc02_judge_question.txt` | `benchmarks/out/phase4/quality/copilot_docx_tc02_judge_description.md` |
| 4 | `03_complex_arch.png`  | `tc03_judge_question.txt` | `benchmarks/out/phase4/quality/copilot_png_tc03_judge_description.md` |
| 5 | `03_complex_arch.pptx` | `tc03_judge_question.txt` | `benchmarks/out/phase4/quality/copilot_pptx_tc03_judge_description.md` |
| 6 | `03_complex_arch.docx` | `tc03_judge_question.txt` | `benchmarks/out/phase4/quality/copilot_docx_tc03_judge_description.md` |

各保存先ファイルには既にヘッダーテンプレート (`# tcXX — quant ...`, `**Question:**`, `## Output`) が書かれている。
Copilot の回答は `## Output` 行の下にそのまま貼り付ければ OK。
`## Output` 下にある HTML コメント行は削除しても残しても良い (採点 UI には影響しない)。

**YYYY-MM-DD** 部分は実施日に書き換えるとメタデータとして便利。

## その後の流れ

6 ファイル全て埋め終わったら、リポジトリルートで:

```bash
python tests/text_vs_image/generate_human_eval_ui.py \
    --extra-quants copilot_png,copilot_pptx,copilot_docx
open tests/text_vs_image/human_eval.html
```

UI で採点 → Export JSON → `generate_copilot_report.py` で日本語レポート生成。

詳細は `tests/text_vs_image/COPILOT_EXPERIMENT.md` を参照。
