# Gemma 4 E4B 量子化 sweep

**ステータス:** 完了
**Phase:** 4
**日付:** 2026-04-17
**実施者:** Claude Opus 4.7（dev rig、RTX 5090、`lms load --gpu off` で CPU-only 強制）
**Phase 3 の勝者ホスト:** LM Studio 0.4.11 Build 1

本プロジェクトのスコープは 1 つのモデルファミリー（**Gemma 4 E4B**）に固定されている。Phase 4 はその 1 モデルの量子化バリアントを比較し、target mini PC にとっての「品質と速度のスイートスポット」を特定する。

## 固定評価セットアップ

- ホスト: LM Studio（Phase 3 勝者、`lms load --gpu off` で CPU-only 強制）
- モデルファミリー: Hugging Face `unsloth/gemma-4-E4B-it-GGUF` の **Gemma 4 E4B**
- 速度シナリオ:
  - S2: `samples/diagram.png`（3 回）
  - S3: `tests/text_vs_image/images/`（4 画像、各 1 回）
- 品質 source of truth: `tests/text_vs_image/test_cases.yaml`
- 品質テストケース: `tc01`, `tc02`, `tc03`, `tc04`
- 品質 judge: **Gemini 2.5 Flash**（外部 API）
- スコアリング規則: `present=1.0`、`partial=0.5`、`missing=0.0`
- 品質評価スクリプト: [tests/text_vs_image/phase4_quality_eval.py](../../../tests/text_vs_image/phase4_quality_eval.py)

## 量子化の候補プール

| 量子化 | ファイルサイズ | LM Studio モデル ID | ロード alias | 備考 |
|---|---|---|---|---|
| Q4_K_M（Phase 3 baseline） | 4.98 GB | `gemma-4-e4b-it@q4_k_m` | `gemma4-e4b-q4` | Phase 3 の速度データを流用 |
| Q5_K_M | 5.48 GB | `gemma-4-e4b-it@q5_k_m` | `gemma4-e4b-q5` | Phase 4 で新規計測 |
| Q8_0 | 8.19 GB | `gemma-4-e4b-it@q8_0` | `gemma4-e4b-q8` | Phase 4 で新規計測 |
| FP16 / BF16 | 15.05 GB | （ロードせず） | — | 除外 — target mini PC（32 GB RAM）に余裕が残らないため |

3 量子化は同一の `mmproj-F16.gguf`（約 990 MB）vision projector を共有している。

## 速度 benchmark サマリ

LM Studio、14 スレッド、CPU-only、median 値：

| 量子化 | S2 wall (s) | S2 tok/s | S2 end-to-end | S3 wall/画像 (s) | S3 tok/s | S3 end-to-end | RSS peak | 失敗件数 |
|---|---|---|---|---|---|---|---|---|
| Q4_K_M | **46.8** | **14.8** | 46.8 s/画像 | **81.9** | **14.6** | 327.6 s / 4 画像 | N/A ¹ | 0 |
| Q5_K_M | 58.5 | 12.8 | 58.5 s/画像 | 89.5 | 12.7 | 358.2 s / 4 画像 | N/A ¹ | 0 |
| Q8_0 | 77.4 | 9.5 | 77.4 s/画像 | 117.9 | 9.3 | 471.7 s / 4 画像 | N/A ¹ | 0 |

¹ RSS peak は harness に計測コードが組み込まれていないため N/A。推論中の LM Studio GUI の表示では、resident RAM はおおむねファイルサイズに比例していた（Q4 / Q5 / Q8 でそれぞれ約 6 / 6.5 / 9 GB）。

速度はファイルサイズに比例する。CPU-only 推論ではメモリ帯域がボトルネックになるため、想定通りの結果：

- Q5_K_M は Q4_K_M より約 25% 遅い（ファイルが 10% 大きいことと、量子化デコード分のオーバーヘッドで説明可能）。
- Q8_0 は Q4_K_M より約 65% 遅い。S2 で 9.5 tok/s は「CPU で使用可能」水準のぎりぎり上。

## 品質スコア サマリ

Judge：**Gemini 2.5 Flash** が `test_cases.yaml` の各 ground_truth_fact について、Gemma の出力内で present / partial / missing を判定。

| 量子化 | tc01 (24 件) | tc02 (20 件) | tc03 (26 件) | tc04 (22 件) | 平均 | 平均記述時間 |
|---|---|---|---|---|---|---|
| **Q4_K_M** | **0.667** | **0.650** | **0.769** | 0.955 | **0.760** | 58.8 s |
| Q5_K_M | 0.667 | 0.550 | 0.673 | **1.000** | 0.722 | 63.4 s |
| Q8_0 | **0.708** | 0.450 | 0.750 | 0.955 | 0.716 | 91.1 s |

生の judge 出力と fact ごとの verdict は [benchmarks/out/phase4/quality/](../../../benchmarks/out/phase4/quality/) を参照。

### 観察された点

1. **Q4_K_M が平均スコア最高（0.760）** — 「量子化が軽ければ軽いほど品質が低い」という直感に反する。正確な解釈としては「N=4 のテストセットでは 3 量子化は統計的に区別がつかない — 0.04 の差は rounding-noise レベルでたまたま Q4 が上に出ただけ」。
2. **tc02 は全量子化で最難**（0.450〜0.650）。UI の before/after 変化を列挙するケース。モデルは差分を整理して説明するのが苦手。
3. **tc04 は全量子化で最易**（0.955〜1.000）。純テキスト文書のケース。ほぼ純粋な OCR タスクで、Gemma 4 E4B の native 多言語 OCR が活きる。
4. **Judge のばらつき**: Gemini 2.5 Flash 自体も sampling を伴う。同一の記述を再度スコアリングすれば若干違う verdict が出うる。量子化間の 0.04 差はこのノイズ幅の中に収まる。

## 選定

- **第一候補の量子化: Q4_K_M**
- **理由:**
  1. 平均品質でトップタイ（0.760）— 本テストセット上で 3 量子化中最も良い。
  2. **最速** — S2 46.8 秒 vs Q5 58.5 秒（+25%）vs Q8 77.4 秒（+65%）。
  3. **メモリ占有最小** — ディスク 4.98 GB / 推論中 RAM 約 6 GB。target mini PC（32 GB RAM）に最も多くの空き容量を残す（OS、ユーザーのデスクトップ、ブラウザなど他プロセス用）。
  4. Phase 3 の baseline として既に Ollama / llama.cpp / LM Studio で実測済み。後でホスト比較に立ち返る時に apples-to-apples の比較ができる。

- **Backup の量子化: Q5_K_M**
- **理由:**
  1. 第一候補の 95% の品質（0.722 / 0.760 = 0.95）— backup 選定ルールの閾値 80% を十分上回る。
  2. 異なる量子化階層のため、将来 Gemma 4 E4B のモデル更新で Q4_K_M が壊れても、Q5_K_M が同時に壊れる可能性は低い。
  3. 速度も「実用域」内（S2 58.5 秒）。同じ mmproj を共有、LM Studio 上のロード方法も同じため、切替の手間は小さい。

## 選定ルールのチェック

- ✅ 第一候補の量子化は品質の（タイ）トップ（平均 0.760）。
- ✅ 第一候補の量子化は S3 を完走（4/4 成功、失敗 0 件）。
- ✅ 第一候補の量子化は最速量子化の 2 倍以内（**これが**最速）。
- ✅ Backup の量子化（Q5_K_M）は Q8 より軽量／高速、Q4 より重い — 品質の上限リファレンスとして機能する。
- ✅ Backup の量子化は第一候補品質の 80% 以上（95%）。
- ✅ Backup の量子化は Q5 が壊れた場合でも Phase 3 baseline の Q4_K_M にフォールバック可能。
- **Q8_0 除外** — 本テストセット上で最遅 AND 品質もトップではない。Q5 より backup に適した理由がない。

## 留保事項

- **N が小さい:** テストケース 4 件、fact 合計約 90 件。品質数値は sampling variance が大きい。10 ケース版にすれば比較がもっと締まる。
- **Judge は単一:** Gemini 2.5 Flash のみ。Gemini 2.5 Pro もしくは別ファミリーを第 2 judge として加えると、judge 固有の偏りが検出できる。
- **デフォルト sampling:** 3 量子化とも LM Studio のデフォルト `temperature`、`top_p`、`max_tokens` を使用。`temperature=0` の決定論的実行で 1 つのノイズ源を消せるが、絶対値は変わる可能性あり。
- **日本語プロンプトのみ:** `tc01..tc04` はいずれも日本語の質問。英語や混合言語のプロンプトでは未評価。

Phase 6（target mini PC 検証）では、Q4_K_M をインストールして実測する。Phase 4 の dev rig 値が target 実測値と比較する baseline となる。
