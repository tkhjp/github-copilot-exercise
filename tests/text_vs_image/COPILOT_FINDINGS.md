# Microsoft Copilot Web — 入力フォーマット比較の主要知見

Phase 4 判断テスト (tc02_judge / tc03_judge) を Microsoft Copilot Web 版に PNG / PPTX / DOCX の 3 フォーマットで投入し、Gemini 2.5 Flash を judge (n_runs=3) として採点した結果から得られた知見。

## TL;DR

1. **「Word に画像を貼り付けて Copilot に渡す」は機能しない** — Copilot Web の DOCX 添付パイプラインは埋込画像を処理しない。スコア 0.000/0.000、Copilot 自身が "画像が見えない、PNG で送ってほしい" と明示する。
2. **PPT (native shape) は PNG より有意に高いスコア** — +0.14 pt (0.844 vs 0.704)。OCR 不要で text が直接読めるぶん、構造化タスクで精度が上がる。
3. **Copilot Web は本実験のローカル Gemma4 E2B 全量子化より PNG / PPTX で優位** — Copilot_pptx 0.844 ≫ q8 0.661 (最良ローカル)。ただし Copilot は n_runs=1 の単発回答なのでばらつきを含む可能性あり。

## スコア総覧 (judgment 2 ケース平均)

| quant | avg | tc02_judge | tc03_judge | n_runs | 備考 |
| --- | --- | --- | --- | --- | --- |
| **copilot_pptx** | **0.844** | 0.929 | 0.759 | 1 | PPT native shape として投入 |
| copilot_png | 0.704 | 0.667 | 0.741 | 1 | PNG を添付 |
| q8 (Gemma4 E2B Q8) | 0.661 | 0.786 | 0.537 | 3 | ローカル最良 |
| q4 (Gemma4 E2B Q4) | 0.619 | 0.738 | 0.500 | 3 | |
| e2b (BF16) | 0.582 | 0.738 | 0.426 | 3 | |
| q5 (Gemma4 E2B Q5) | 0.579 | 0.714 | 0.444 | 3 | |
| **copilot_docx** | **0.000** | 0.000 | 0.000 | 1 | PNG を埋め込んだ DOCX — 画像は読まれていない |

Gemini judge 安定性: 全 (quant, case) で agreement ≥ 0.90、std ≤ 0.041。

## 主要知見の詳細

### 1. DOCX + 埋込画像 → Copilot は画像を無視する

Copilot Web の DOCX 添付処理パイプラインは本文テキストのみを抽出し、`<w:drawing>` 内に埋め込まれた PNG を視覚解析に回していないと推定される。

**根拠**: tc02_judge の DOCX 版で、Copilot は 4 つの吹き出しに一切触れず、以下のように明示的に画像取得を要求してきた:

> 「現在の添付ドキュメントには...個々の「4つの赤い吹き出し（＝各変更要求）」の具体内容が含まれていません」

tc03_judge の DOCX 版も同様に:

> 「添付ファイルの抽出テキストには設問文のみが含まれており、実際のアーキテクチャ図（画像）が抽出結果に含まれていません」

→ 全 16 reasoning point が missing、3 run 全一致 (agreement 1.0)。ランダムな失敗ではなく、**pipeline の仕様レベルの限界**。

### 2. PPTX (native shape) > PNG (+0.14 pt)

PPTX では各 UI 要素や AWS コンポーネントが独立した shape + text として保存されており、Copilot は OCR を経由せずに直接 text を読めるため、以下のようなケースで明確に優位:

| reasoning point | PNG 判定 | PPTX 判定 | 解釈 |
| --- | --- | --- | --- |
| tc02_judge j07 (4 変更の並列実装可否) | **missing** | present | PNG 版では並列性に触れなかった Copilot が、PPT では触れている |
| tc02_judge j06 (最大リスク = 変更3) | partial | **present** | 判断の明示度が上がる |
| tc03_judge j06 (第4層 = RDS/ElastiCache) | **missing** | partial | 階層判定の精度向上 |

ただし 100% 優位ではない — **tc03_judge j08 (青緑/シアン太線 = read-only)** は PNG / PPTX ともに missing。細い色の差 (緑 vs シアン) は PNG/PPTX どちらでも LLM が識別しきれない可能性あり。

### 3. Copilot_pptx は本実験ローカル全量子化を上回る

q8 (Gemma4 E2B Q8) の 0.661 に対し copilot_pptx は 0.844 と +0.18 pt。ただし:

- Copilot は **n_runs=1** (単発回答)、ローカル LLM は **n_runs=3 の多数決**
- 絶対値の差は大きいが、Copilot のばらつきは未計測 — 厳密比較には 3 run 取る必要あり
- Copilot のモデル基盤 (GPT-4o / GPT-4o-mini 等) はローカル 8GB 量子化モデルに対して 100×~1000× のパラメータ数、直接比較は参考程度

業務示唆としては「**ローカル LLM は Copilot には及ばないが、ローカル量子化間の差 (q4~q8+e2b で avg 0.579~0.661) よりフォーマット差 (PNG→PPT で +0.14) の方が大きい**」ことが重要 — 精度向上の施策としてまずフォーマット最適化が効く可能性がある。

## 業務への示唆

1. **スクリーンショットは必ず画像ファイル単独で送る** — Word docx に貼り付けた状態では Copilot は見ない。
2. **可能なら PowerPoint に変換する** — オリジナルが図表ベースのドキュメントなら、PPT として共有するとテキスト情報が構造化されて渡り、LLM 側で読み違いが減る。ビジネス文書の共有フォーマット選択の指針になる。
3. **色のみで意味を持たせた可視化は要注意** — シアンと緑のような近接色は LLM でも識別しきれない (本実験の j08)。凡例テキストで補強する / ラベルを図中に直接書くのが安全。
4. **"同じ内容を同じ LLM に渡しても" フォーマットで結果が変わる** — 実務では複数フォーマットで検証してから運用に載せるのが望ましい。

## 本実験の制約

- **Copilot 側の n_runs=1** — 単発応答のばらつきは測定していない。
- **2 ケースのみ** — tc02_judge / tc03_judge のみで判断。より広範な検証には追加ケースが必要。
- **Gemini judge を単独採用** — judge 間バイアスは測定していない。別 judge (例: Claude, GPT-5) との対照が理想。
- **手動アップロード** — Copilot Web の UI 経由の応答で、API と挙動が異なる可能性。
- **PPTX の再現度** — 元 PNG を python-pptx で近似再構成。視覚は似ているがピクセル完全一致ではない。ただし本実験では text 内容の同型性を優先しており、この差は結果に影響しない。

## 生データ

全 scores.json / 回答 MD / Gemini 判定 per-run は commit 済み:

- `benchmarks/out/phase4/quality/copilot_{png,pptx,docx}_tc0{2,3}_judge_description.md`
- `benchmarks/out/phase4/quality/copilot_{png,pptx,docx}_tc0{2,3}_judge_scores.json`
- `benchmarks/out/phase4/quality/copilot_{png,pptx,docx}_tc0{2,3}_judge_judge_run{1,2,3}_scores.json`
- `benchmarks/out/phase4/quality/copilot_{png,pptx,docx}_judgment_summary.json`

人手採点フェーズは `tests/text_vs_image/human_eval_copilot_compare.html` を起動して実施 (Gemini 判定の信頼性確認用)。
