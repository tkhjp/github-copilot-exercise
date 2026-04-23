# Microsoft Copilot 抽出プロンプト設計実験 設計書

**作成日:** 2026-04-24
**対象リポジトリ:** `/Volumes/mac_hd/work/github-copilot-exercise`
**ステータス:** Draft — ユーザーレビュー待ち
**前段:** [COPILOT_FINDINGS.md](../../../tests/text_vs_image/COPILOT_FINDINGS.md) — PNG/PPTX/DOCX 比較実験の知見

---

## 1. 目的と範囲

### 1.1 背景

将来的にお客様へ提供する solution では、画像処理コスト（OCR 基盤構築・API トークン消費）の低減が経営課題になる。そこで **Microsoft Copilot Chat に画像/PPT から verbatim なテキスト抽出を肩代わりさせる** ことで、下流 LLM に渡す前処理段階の負担を軽減するアプローチが候補に上がっている。

前段の検証（[COPILOT_FINDINGS.md](../../../tests/text_vs_image/COPILOT_FINDINGS.md)）で以下が判明:

- **Copilot Web は DOCX に埋め込んだ画像を処理しない** (score 0.000、Copilot 自身が「画像が見えない」と明示) → DOCX は今回実験のスコープ外
- **PPTX (native shape) は PNG より verbatim 抽出に優位** (0.844 vs 0.704, +0.14pt)
- しかし、実験に用いた材料 (tc02_judge, tc03_judge) は**現場文書として単純すぎる** — 抽出プロンプトの品質差が見分けづらい

### 1.2 核心命題

> **実際の業務ドキュメントに近い複雑度のサンプルを用意し、PNG / PPTX 各フォーマット向けの verbatim 抽出プロンプトを開発・評価する。** お客様がこの 2 種の抽出プロンプトを運用に組み込めば、Copilot Chat を低コストな "OCR + 構造抽出" 前処理として利用できる。
>
> プロンプト自体の **設計・実行** は実験主導者 (human operator) が Copilot Web で手動で試す。本設計書は、そのプロンプト試行のための **材料 (test corpus)** と **評価インフラ (Gemini judge + per-slide scoring)** を整える。

### 1.3 目的

1. **8 pattern (P1-P8) の現場想定 slide を含む PPTX ファイル 1 本 + 各 slide のスクショ PNG 8 枚を生成** (test corpus)
2. 各 slide の **ground truth (抽出すべきテキスト事実の列挙)** を自動吐出
3. **Gemini 2.5 Flash を judge とする評価パイプライン** を構築 — recall と hallucination の 2 指標
4. **同 corpus 上で複数プロンプトを試行・比較できるワークフロー** を整える
5. 実験主導者がプロンプト試行を行い、**最終的に PNG / PPTX 各 1 本の "本番用" プロンプトを確定する**（確定作業は実装後の別フェーズ）

### 1.4 範囲内

- 8 pattern × (PPTX 1 ファイル + PNG 8 枚) の材料生成スクリプト
- Ground truth YAML の自動生成
- Gemini judge を再利用した per-slide 評価スクリプト (recall + hallucination)
- 複数プロンプト試行結果の集計・比較レポートスクリプト
- 運用ドキュメント (user が Copilot Web でどうプロンプトを走らせ、結果をどこに保存するか)

### 1.5 範囲外

- **DOCX フォーマットの評価** — 前段で画像無視が確定済みのため除外
- **プロンプト自体の設計・試行の自動化** — user が Copilot Web で手動実行
- **Copilot API 経由の自動呼び出し** — Web 版 (ブラウザ) を前提、API 版は今回不要
- **ハルシネーション自動修正** — 検出のみ、修正戦略は本実験で扱わず
- 具体的な最終プロンプト本文の確定 — 材料・評価基盤を提供するのが本設計の責任、プロンプト決定は後続フェーズ

---

## 2. Test Corpus 設計

### 2.1 全体像

1 本の PPTX ファイルに 8 slides (P1-P8) を含め、**各 slide を 1 つの pattern に対応させる**。同じ内容を PNG でも 8 枚で提供し、「同一内容・異なるフォーマット」の対照を保つ。

Ground truth は各 slide につき **抽出すべきテキスト事実のリスト** を YAML で持つ。形式は Phase 4 の `ground_truth_facts` を踏襲。

### 2.2 Pattern 別 slide 仕様

日本語をメインとし、コードや識別子（変数名・API 名・ステータスラベル等）は英語を許容。各 slide の情報量は以下の目安:

| # | Pattern | 主要要素 | GT fact 数の目安 |
|---|---|---|---|
| **P1** | UI/画面レビュー型 | 勤怠アプリ画面 SS + 赤矢印 4 本 + 吹き出し注釈 4 個 | 〜25 |
| **P2** | Before/After 比較型 | 旧/新画面 SS 2 枚 + 差分矢印 3 本 + 差分ラベル | 〜20 |
| **P3** | 工程フロー型 | ログイン→商品→カート→決済→完了 の 5 画面 SS + 番号付き矢印 | 〜25 |
| **P4** | ダッシュボード + 解釈注釈 | 棒グラフ + 円グラフ + KPI カード 3 枚 + 解釈吹き出し 3 個 | 〜30 |
| **P5** | 階層ドリルダウン | 上: システム 5 モジュール構成 / 下: 1 モジュール拡大図 + 設定表 | 〜25 |
| **P6** | レビュー反映 (赤入れ) | モック 1 枚 + 番号付き赤コメント 15 個 + 指示線 | 〜35 |
| **P7** | 混合ダッシュボード | 表 (5×4) + 棒グラフ + SS + コード片 + 箇条書き | 〜35 |
| **P8** | 組織図 + ノード SS 補足 | 3 階層 10 ノード + 各ノードの氏名・役職・顔写真風サムネ | 〜30 |

**合計 GT fact 数**: ~225 件程度 (slide 平均 ~28 件)。

### 2.3 設計方針

- **Pattern の具体内容** (画面に描画される実データ) は [extraction_spec.py](../../../tests/text_vs_image/extraction/extraction_spec.py) に **1 ファイルに集中**。PIL/python-pptx/GT YAML 生成の 3 者がこの同じ spec を読む — 単一事実源 (single source of truth)
- PPTX は python-pptx で native shape として描画、PNG は PIL で独立に pixel-perfect 描画 — Phase 4 の tc02/tc03 で確立した方式をそのまま踏襲
- PNG は**実 PPTX のレンダリングを screenshot したものではない**が、spec 同期により「同一内容の別フォーマット」として等価。LibreOffice 等の追加依存を避け、pure Python で再現可能
- 各 slide の背景色や装飾は統一し slide テンプレート風に仕上げるが、各 pattern の情報密度は現場想定のまま確保

---

## 3. 評価設計

### 3.1 Metric (再掲: 前段会話で合意済み)

**Metric B: recall + hallucination の 2 軸**

- **Recall**: GT fact の各項目について `present` (1.0) / `partial` (0.5) / `missing` (0.0) を Gemini が判定、平均スコアを slide 単位で集計
- **Hallucination**: Copilot 出力中の "元 slide に存在しない情報" を Gemini が検出、件数カウント + 具体例列挙

### 3.2 評価粒度 (再掲: 前段会話で合意)

**Per-slide scoring** — PPTX の 1 回の Copilot 応答が 8 slides 分をカバーする場合、**各 slide 分のテキストを分離して個別採点**する。

分離方式:
- Copilot 応答に slide 見出し (例: `## Slide 1` 等) がある場合はそれで分割
- なければ Gemini judge 側で「この応答から slide N に該当する部分のみを抽出し、slide N の GT と照合せよ」と指示 (段階的 prompt)

PNG は 1 枚 = 1 応答 = 1 GT と素直に対応。

### 3.3 Gemini judge prompt の拡張

既存 `phase4_quality_eval.py` の `JUDGE_PROMPT_EXTRACTION` をベースに以下を追加:

- **Hallucination 判定用 prompt** を新規追加 — 応答中に GT に無い重要情報が含まれていないか評価 (件数 + 例)
- **PPTX per-slide 分離用 prompt** — 大きな Copilot 応答から slide N 相当部分を抽出

`n_runs=3` で多数決。既存の agreement / verdict_mode ロジックをそのまま流用。

---

## 4. ワークフロー

### 4.1 実験主導者 (user) のフロー

```
1. [1 回だけ] python tests/text_vs_image/extraction/generate_extraction.py
   → extraction_test.pptx + 8 PNG + ground_truth.yaml が生成される

2. [プロンプト試行 1 回ごとに] prompt_id を決めて (例: "p01_baseline")

3. Copilot Web (https://copilot.microsoft.com/) を開く

4. PPTX 試行:
   - extraction_test.pptx をアップロード
   - プロンプトを貼り付け、送信
   - 回答をコピーして
     benchmarks/out/extraction/{prompt_id}/pptx_response.md に保存

5. PNG 試行 (8 回):
   - p01.png をアップロード、プロンプト貼付、回答を
     benchmarks/out/extraction/{prompt_id}/png_p01_response.md に保存
   - p02-p08 も同様

6. python tests/text_vs_image/extraction/judge_extraction.py --prompt-id {prompt_id}
   → Gemini judge が recall + hallucination を採点、
     benchmarks/out/extraction/{prompt_id}/scores/ に保存
     ターミナルに per-slide スコア表を出力

7. 複数 prompt_id 試した後:
   python tests/text_vs_image/extraction/extraction_report.py
   → benchmarks/out/extraction/ 下の全 prompt_id を横断で比較した
     Markdown レポート (日本語) を生成
```

### 4.2 プロンプト命名規約

- `{format}_{strategy}_v{N}` 形式を推奨 (例: `pptx_detailed_v1`, `png_cot_v2`)
- フォーマットと実験対象戦略を明記、バージョン管理可能
- ただし厳格なチェックはせず、ディレクトリ名として任意の文字列を許容

---

## 5. ファイル/ディレクトリ構成

### 5.1 新規作成

```
tests/text_vs_image/extraction/
├── extraction_spec.py              # 8 pattern の canonical spec (pure Python dict)
├── generate_extraction.py          # spec → PPTX + 8 PNG + GT YAML 一括生成
├── judge_extraction.py             # Copilot 応答 → Gemini judge → per-slide score
├── extraction_report.py            # 全 prompt 横断の比較 Markdown レポート生成
├── README.md                       # ワークフロー説明 (日本語)
├── extraction_test.pptx            # ★ 生成物: Copilot 用アップロードファイル
├── p01_ui_callouts.png             # ★ 生成物: PNG 試行用
├── p02_before_after.png
├── p03_process_flow.png
├── p04_dashboard_annotated.png
├── p05_hierarchical_drilldown.png
├── p06_review_comments.png
├── p07_mixed_dashboard.png
├── p08_org_chart.png
└── ground_truth.yaml               # ★ 生成物: per-slide fact list

benchmarks/out/extraction/
└── {prompt_id}/                    # プロンプト試行 1 回につき 1 ディレクトリ
    ├── prompt.md                   # 使用したプロンプト全文 (user が貼付)
    ├── pptx_response.md            # Copilot の PPTX 応答
    ├── png_p01_response.md         # PNG 試行の応答
    ├── png_p02_response.md
    ├── ...
    ├── png_p08_response.md
    └── scores/
        ├── pptx_scores.json        # per-slide scores for PPTX
        ├── png_p01_scores.json
        ├── ...
        └── summary.json            # prompt_id の集計
```

### 5.2 再利用する既存コード

- `tests/text_vs_image/phase4_quality_eval.py` の以下を import:
  - `JUDGE_PROMPT_EXTRACTION` (ベース prompt)
  - `judge_with_gemini()`, `extract_json()`, `_mode_and_agreement()`, `_stdev()`
  - `SCORE_MAP`
- `tests/text_vs_image/judge_pasted_descriptions.py` の構造 (pasted MD → Gemini judge → scores.json) を踏襲
- 既存の `python-pptx` / PIL 使用例は `generate_test_pptx.py` / `generate_test_images.py` を参考

### 5.3 変更する既存コード

なし。新規ファイルのみ追加。

---

## 6. 実装フェーズ

### Phase 0: 材料生成

- `extraction_spec.py`: 8 pattern の dict を書き下し
- `generate_extraction.py`: spec → 3 artifacts 生成、Phase 4 の generator パターン流用

### Phase 1: 評価インフラ

- `judge_extraction.py`:
  - per-slide judge (recall with `JUDGE_PROMPT_EXTRACTION` 流用)
  - hallucination judge (新規 prompt)
  - PPTX 応答の slide 分離 (prompt で Gemini に任せる)
- `extraction_report.py`: 全 prompt_id の横断レポート

### Phase 2: 試行ドライブ (user 主導)

- user が Copilot Web でプロンプトを試行
- 1 回の試行につき 9 ファイル (pptx_response + png p01-p08) を benchmarks/out/extraction/{prompt_id}/ に保存
- `judge_extraction.py` で採点、`extraction_report.py` で比較

### Phase 3: プロンプト確定 (別 session で計画)

本設計書のスコープ外。試行データが貯まった後、別の brainstorming session で最終プロンプト 2 本 (PNG / PPTX) を選定・文書化する。

---

## 7. 検証項目

### 7.1 材料生成スクリプトの validation

1. `extraction_test.pptx` を Keynote で開き、8 slides が意図通りに描画されていること
2. 8 PNG が PPTX の各 slide と内容的に対応していること
3. `ground_truth.yaml` の fact 数が 2.2 表の目安範囲に収まっていること

### 7.2 評価パイプラインの validation

1. ダミー Copilot 応答 (GT を丸写し) を judge にかけ、スコアが 1.0 近辺になる
2. 逆にダミー空応答を judge にかけ、スコアが 0.0 になる
3. 意図的に hallucination を入れた応答で hallucination カウントが > 0 になる
4. PPTX 応答の slide 分離が正しく動作し、各 slide の GT と正しく照合される

### 7.3 End-to-end validation

1. 1 種類のシンプルなプロンプト (例: `png_baseline`) で 9 回 Copilot を実行 → MD 保存
2. `judge_extraction.py --prompt-id png_baseline` 実行、per-slide score が全 slide で出力される
3. `extraction_report.py` で Markdown レポートが生成される

---

## 8. リスクと緩和

| リスク | 緩和策 |
|---|---|
| Copilot Web が 8 slide の PPTX に対し truncated response を返す | 応答全文保存を強制、judge で "見えていない slide" をログ化、分割投入の案内を README に記載 |
| Copilot Web が同じプロンプトで確率的に異なる応答を返す | 評価は応答テキストに対して決定的、ばらつきは同じ `prompt_id` で複数試行で測定 (後続フェーズ) |
| Gemini judge の hallucination 判定が不安定 | `n_runs=3` の多数決、agreement が 0.67 未満なら警告ログ |
| 8 pattern で現場の多様性を代表しきれていない | 設計書 6.3 の "後続フェーズ" で held-out サンプルを追加投入、既存 8 件と結果を突き合わせる |
| PIL 生成の PNG が Keynote/PowerPoint 実レンダリングと見え方が違う | 文字・図形・配置は正確に再現する方針 (内容抽出が目的でピクセル忠実は不要、前段実験で同方針で問題なかった) |
| PPTX の slide 分離が不完全 (Copilot 応答構造次第) | Gemini に応答全文 + 対象 slide id を渡して該当部分のみ判定する prompt で回避 |

---

## 9. 用語

- **verbatim 抽出**: 要約・解釈を加えず、文書中のテキストをそのまま書き起こす行為
- **recall**: GT fact のうち応答でカバーされた割合 (1.0 / 0.5 / 0.0 の平均)
- **hallucination**: 応答中に含まれる、元文書には存在しない情報
- **prompt_id**: 1 回のプロンプト試行に対する人間可読 ID (ディレクトリ名として使用)
- **pattern (P1-P8)**: 現場想定の 8 種類の slide 構造類型 (UI レビュー / Before-After / 工程フロー / ダッシュボード / 階層 / 赤入れ / 混合 / 組織図)

---

## 10. 関連ドキュメント

- [COPILOT_FINDINGS.md](../../../tests/text_vs_image/COPILOT_FINDINGS.md) — 前段実験の知見 (PNG/PPTX/DOCX 比較)
- [COPILOT_EXPERIMENT.md](../../../tests/text_vs_image/COPILOT_EXPERIMENT.md) — 前段実験のワークフロードキュメント
- [tests/text_vs_image/phase4_quality_eval.py](../../../tests/text_vs_image/phase4_quality_eval.py) — 既存の Gemini judge 実装 (本実験で再利用)
- [tests/text_vs_image/judge_pasted_descriptions.py](../../../tests/text_vs_image/judge_pasted_descriptions.py) — 既存の "pasted response → judge" パターン (本実験で踏襲)
- [tests/text_vs_image/generate_test_pptx.py](../../../tests/text_vs_image/generate_test_pptx.py) — 既存の python-pptx 使用例 (本実験で流用)
- [tests/text_vs_image/generate_test_images.py](../../../tests/text_vs_image/generate_test_images.py) — 既存の PIL 使用例 (本実験で流用)
