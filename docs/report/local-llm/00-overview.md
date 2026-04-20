# ローカル LLM Appliance 検証 — 全体概要

**作成日:** 2026-04-17
**対象リポジトリ:** [tkhjp/github-copilot-exercise](https://github.com/tkhjp/github-copilot-exercise)

このディレクトリ（`docs/report/local-llm/`）は、社内向けローカル LLM appliance 選定プロジェクトの調査・実測レポート群です。本ドキュメントはその**索引**で、全 7 フェーズの内容・成果物・進捗を一覧化しています。

---

## 1. プロジェクトの目的

本プロジェクトの主目的は、**Splashtop 経由でアクセスする隔離端末（社内機房の Windows mini PC）上に LLM を serve し、その画像認識能力がどの程度あるかを調査すること**である。データを社外に出さずに完結する構成での capability research。

### 背景

- 社内ポリシーで GitHub Copilot Chat の preview 機能（画像入力など）が無効化されており、Copilot Chat 単体では画像を扱えない。
- 先行 PoC ([image-describer-poc](../image-describer-poc-verification.md)) では Copilot から `run_in_terminal` 経由で CLI を呼び、CLI が外部 Gemini API に画像を送って Markdown を得る構成を採った。これは画像データが社外に出るため、governance 観点では暫定策にすぎない。
- 隔離端末上のローカル LLM が画像認識をどこまで実用レベルでこなせるかが分かれば、データを社外に出さずに同種のユースケースを成立させる道筋が見えてくる。

### 本プロジェクトの位置付け

- **調査対象:** 隔離端末（Splashtop 経由でアクセス、Windows mini PC、CPU + iGPU のみ、外部通信なし前提）上で動かすローカル LLM の **画像認識能力**。
- **比較ベースライン:** 既存の Gemini API 経由 image-describer PoC の出力を「事実上の上限」として参照。ローカル LLM がどこまで近づけるかを測る基準にする（即時に置き換えるかどうかを判定するためではなく、capability gap を把握するため）。
- **アクセス経路:** Splashtop は「隔離端末に入るための手段」であり、置き換え対象ではない。

詳細な背景・命題・スコープは [設計書（design spec）](../../superpowers/specs/2026-04-15-local-llm-appliance-design.md) を参照。

---

## 2. 対象機材

| | dev rig（実装・実測機） | target mini PC（配備先） |
|---|---|---|
| CPU | （高性能） | Intel **i5-14500T**（6P+8E、低 TDP） |
| GPU | RTX 5090（CPU-only モード強制） | なし（Intel UHD 770 iGPU のみ） |
| RAM | — | 32 GB |
| OS | — | Windows 11 Pro 24H2 |

dev rig 上の全実測は **CPU-only モードを強制**し、target mini PC の挙動を近似する。

---

## 3. 全 7 フェーズ一覧

| Phase | 内容 | 主要成果物 | 状態 |
|:---:|---|---|:---:|
| **Phase 1** | ツール調査（7 候補から 3 ツール選定） | [01-tool-matrix.md](01-tool-matrix.md) | ✅ 完了 |
| **Phase 2** | benchmark harness + ローカル LLM client 実装 | [Phase 0/2/5 plan](../../superpowers/plans/2026-04-15-local-llm-appliance-phase0-2-5.md) + コード | ✅ 完了 |
| **Phase 3** | 選定 3 ツールの実測 benchmark（host 選定） | [02-tool-shortlist-benchmark.md](02-tool-shortlist-benchmark.md) | ✅ 完了 |
| **Phase 4** | 量子化 sweep + 品質スコアリング（model 選定） | [03-model-selection.md](03-model-selection.md) | ✅ 完了 |
| **Phase 5** | プロトタイプ実装（`LLM_BACKEND=local` で既存 CLI を切替可能に） | [Phase 0/2/5 plan](../../superpowers/plans/2026-04-15-local-llm-appliance-phase0-2-5.md) + コード | ✅ 完了 |
| **Phase 6** | target mini PC 上での実測検証 | [04-target-validation.md](04-target-validation.md) | ⏳ 未着手 |
| **Phase 7** | 最終統合レポート（Phase 1〜6 の集約 + 採用判断） | [local-llm-selection-report.md](../local-llm-selection-report.md) | ⏳ 未着手 |

実行手順書（runbook）：[05-measurement-runbook.md](05-measurement-runbook.md)

---

## 4. 各フェーズの詳細

### Phase 1 — ツール調査

**何をしたか:** 主流のローカル LLM ホスティングツール 7 種（Ollama、llama.cpp、LM Studio、IPEX-LLM、OpenVINO-GenAI、text-generation-webui、vLLM）を desk research で評価し、Phase 3 で実測する候補を 3 種に絞り込んだ。

**結論:**

- 選定: **Ollama / llama.cpp / LM Studio**
- 除外: vLLM, OpenVINO-GenAI, IPEX-LLM, text-generation-webui

**判断軸:** Windows native で OpenAI 互換 HTTP を素直に出せること、閉域運用のしやすさ、Windows サービス化の摩擦の小ささ。

**成果物:** [01-tool-matrix.md](01-tool-matrix.md)

---

### Phase 2 — benchmark harness + ローカル LLM client 実装

**何をしたか:** ツール非依存の benchmark harness（S1 text-only / S2 vision-single / S3 vision-pptx-batch の 3 シナリオ）と、OpenAI 互換エンドポイントを叩く統一 adapter (`benchmarks/adapter/openai_client.py`) を実装。

**到達点:** 41 / 41 tests green（unit + integration）。

**重要な設計判断:** adapter は Phase 5 のプロトタイプ client (`tools/lib/local_llm_client.py`) と同一のものを再利用する。これにより benchmark の数値と実運用の数値が apples-to-apples になる。

**成果物:** [Phase 0/2/5 plan](../../superpowers/plans/2026-04-15-local-llm-appliance-phase0-2-5.md) + `benchmarks/` ディレクトリのコード

---

### Phase 3 — 選定 3 ツールの実測 benchmark（host 選定）

**何をしたか:** Ollama / llama.cpp / LM Studio に Gemma 4 E4B（Q4_K_M）をロードし、CPU-only モードで S1 / S2 / S3 を実測。3 ホストを比較して Phase 4 以降に進める「勝者」ホストを選定。

**結論: 勝者は LM Studio**

- 生の tok/s は 3 ホストとも 14〜16 で実質同じ（全て llama.cpp ggml バックエンドを共有しているため）
- 差は主に応答長と運用性に出る — LM Studio は `lms` headless / `--gpu off` / `lms import --hard-link` などで Windows 運用が最も滑らか
- Phase 3〜7 plan の選定ルール「20% 以内なら運用性優先」を適用

**成果物:** [02-tool-shortlist-benchmark.md](02-tool-shortlist-benchmark.md) + raw データ `benchmarks/out/phase3/`

---

### Phase 4 — 量子化 sweep + 品質スコアリング（model 選定）

**何をしたか:** LM Studio 上で Gemma 4 E4B の Q4_K_M / Q5_K_M / Q8_0 をそれぞれロード、S2 / S3 速度実測 + `tc01..tc04` で品質を Gemini 2.5 Flash judge で採点。**2026-04-20 追加:** Gemma 4 **E2B** Q4_K_S（unsloth GGUF、mmproj-F16 同梱）も同じ条件で測定し、モデルサイズバリアント軸を追加。**さらに同日、判断テスト `tc02_judge` / `tc03_judge`（reasoning_points を持つケース）も全 4 候補で走らせ、抽出と判断を別軸として比較できるように拡張**。LLM judge に単一依存しないため、人手スコア入力用の静的 UI（[`tests/text_vs_image/generate_human_eval_ui.py`](../../../tests/text_vs_image/generate_human_eval_ui.py)）を追加しクロスチェック経路を整備。

**結論:**

- **スループット重視の第一候補: Gemma 4 E2B Q4_K_S**（約 3 GB） — E4B Q4 の約 1.9 倍のスループット（S2 26 s / S3 33 s per image）、品質は 93%
- **品質重視の第一候補: Gemma 4 E4B Q4_K_M**（約 5 GB） — E4B 量子化 sweep 内で品質トップ、特に tc03 複雑アーキ図で優位
- **backup: Gemma 4 E4B Q5_K_M** — E4B Q4 と異なる量子化階層で redundancy、品質 95%

**読み取れること:**

- E4B 3 量子化の品質差（0.72〜0.76）は judge の sampling variance 範囲内で区別不能、Q4 が最速・最軽量で優勢、Q8 を排除
- **E2B の追加で候補が 2 軸に分岐** — 速度はパラメータ数が支配（E2B 4.6B → E4B 7.5B で約 1.9 倍差）、抽出品質は用途依存（UI 差分列挙で E2B 優位、複雑な構造図で E4B Q4 優位）
- **判断テストの量子化差は統計的ノイズ内（n_runs=3 集計）:** Q8 0.661 ±0.104 > Q4 0.619 ±0.082 > E2B 0.582 ±0.144 > Q5 0.579 ±0.063。全差が 1σ 以内で統計的に区別不能。単発ランで出ていた「E2B が首位」の見立ては撤回 — 3 回平均では ±0.14 のブレ幅の中に入る。E2B は std が最大で、判断系では出力が run ごとに振れやすい性質が明確になった。`tc03_judge`（AWS 構成視覚読解）は全候補で 0.43〜0.54、共通弱点として残る。
- 途中で `google/gemma-3n-E2B-it` も検討したが、2026-04-20 時点で llama.cpp が Gemma 3n の vision 経路を未サポートのため、全 GGUF 配布が text-only で vision benchmark 不可 — 採用は **Gemma 4 E2B**

**成果物:** [03-model-selection.md](03-model-selection.md) + `benchmarks/out/phase4/` + 評価スクリプト [`tests/text_vs_image/phase4_quality_eval.py`](../../../tests/text_vs_image/phase4_quality_eval.py) + 人手 UI [`tests/text_vs_image/generate_human_eval_ui.py`](../../../tests/text_vs_image/generate_human_eval_ui.py) / [`import_human_scores.py`](../../../tests/text_vs_image/import_human_scores.py)

---

### Phase 5 — プロトタイプ実装

**何をしたか:** 既存の `tools/lib/gemini_client.py` と同じインタフェースを持つ `tools/lib/local_llm_client.py` を実装し、`tools/describe_image.py` / `describe_pptx.py` / `describe_docx.py` の 3 CLI に `LLM_BACKEND=gemini|local` の dispatcher を追加。

**運用方法:**

```bash
# 既存（Gemini API 経由、デフォルト）
python tools/describe_image.py samples/diagram.png

# 本地 LLM（LM Studio + Gemma 4 E4B）に切替
LLM_BACKEND=local LLM_BASE_URL=http://127.0.0.1:1234/v1 LLM_MODEL=gemma4-e4b-bench \
  python tools/describe_image.py samples/diagram.png
```

**Gemini path は完全に温存**（regression なし）。

**成果物:** [Phase 0/2/5 plan](../../superpowers/plans/2026-04-15-local-llm-appliance-phase0-2-5.md) + `tools/lib/local_llm_client.py` + dispatcher 改修

---

### Phase 6 — target mini PC 上での実測検証

**何をするか（未着手）:** target mini PC（i5-14500T、32 GB RAM、iGPU only）に LM Studio をインストールし、S2 / S3 を 1 回ずつ走らせて、dev rig CPU-only モードの値と比較する。候補は 2 段構え。

**判定基準:**

- 第 1 段: **Gemma 4 E4B Q4_K_M**（品質重視） — 差が **2x 以内** → 「使用可能」として採用
- 第 1 段が 2x を超えるが完走 → 「限界的」、第 2 段へ
- 第 1 段が完走しない（timeout / OOM） or 「限界的」の場合、第 2 段: **Gemma 4 E2B Q4_K_S**（スループット重視） — Q4 の 60% サイズ、1.9 倍スループット、品質 93%。target 側で通る可能性が高い
- E4B Q5_K_M は E4B 内 backup として温存

**成果物（予定）:** [04-target-validation.md](04-target-validation.md)（現状はテンプレート）

---

### Phase 7 — 最終統合レポート

**何をするか（未着手）:** Phase 1〜6 の結果を 1 本のレポートに集約し、「採用するか／どう配備するか／次にすべきは何か」を意思決定者向けにまとめる。

**必須セクション:**

1. Executive summary
2. 背景と目的
3. ツールマトリクスサマリ
4. 選定 benchmark 結果
5. 量子化 sweep 結果
6. target 機検証結果
7. プロトタイプの使用方法
8. リスクと次ステップ

**最終結論で名指すべき項目:**

- 採用ホスト（現状: LM Studio）
- スループット重視の第一候補（現状: Gemma 4 E2B Q4_K_S）
- 品質重視の第一候補（現状: Gemma 4 E4B Q4_K_M）
- backup（現状: Gemma 4 E4B Q5_K_M）

**成果物（予定）:** [local-llm-selection-report.md](../local-llm-selection-report.md)（現状はテンプレート）

---

## 5. ファイル構成（このディレクトリ）

```
docs/report/local-llm/
├── 00-overview.md                       ← 本ファイル（索引）
├── 01-tool-matrix.md                    ← Phase 1: ツール調査
├── 02-tool-shortlist-benchmark.md       ← Phase 3: ホスト選定 benchmark
├── 03-model-selection.md                ← Phase 4: 量子化 sweep
├── 04-target-validation.md              ← Phase 6: target 機検証（テンプレート）
└── 05-measurement-runbook.md            ← 実行手順書（Phase 3/4/6/7 共通）

docs/report/
└── local-llm-selection-report.md        ← Phase 7: 最終統合レポート（テンプレート）
```

関連プラン・スペック：

```
docs/superpowers/specs/
└── 2026-04-15-local-llm-appliance-design.md   ← 全体設計

docs/superpowers/plans/
├── 2026-04-15-local-llm-appliance-phase0-2-5.md   ← Phase 0/2/5 実装計画
└── 2026-04-16-local-llm-appliance-phase3-4-6-7.md ← Phase 3/4/6/7 実行計画
```

---

## 6. 進捗ステータス

- ✅ **Phase 1〜5 完了** — 採用候補（LM Studio + Gemma 4 E2B Q4_K_S [throughput] / E4B Q4_K_M [quality]）まで決定済み、プロトタイプ動作確認済み、人手クロスチェック UI も整備済み
- ⏳ **Phase 6 未着手** — target mini PC へのアクセス手配が次のアクション
- ⏳ **Phase 7 未着手** — Phase 6 完了後に着手
