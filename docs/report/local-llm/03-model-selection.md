# Gemma 4 E4B 量子化 sweep（Phase 4）

**ステータス:** 完了
**Phase:** 4
**日付:** 2026-04-17
**実施者:** Claude Opus 4.7（dev rig、RTX 5090、`lms load --gpu off` で CPU-only 強制）
**Phase 3 の勝者ホスト:** LM Studio 0.4.11 Build 1

---

## 1. 結論

**第一候補: Q4_K_M、backup: Q5_K_M、Q8_0 は除外。**

| 項目 | 内容 |
|---|---|
| **第一候補** | **Gemma 4 E4B Q4_K_M**（約 5 GB） |
| **backup** | **Gemma 4 E4B Q5_K_M**（約 5.5 GB） |
| **除外** | Q8_0（約 8 GB） — 最遅 AND 品質もトップではない、Q4 に完全に支配される |
| **判定 host** | LM Studio（Phase 3 勝者）に固定 |

### Q4_K_M の決め手（3 点）

1. **品質トップタイ**（avg 0.760 ≧ Q5 0.722 ≧ Q8 0.716）— 統計的差はないがダウンサイドなし
2. **最速**（S2 46.8 秒 vs Q5 58.5 秒（+25%）vs Q8 77.4 秒（+65%））
3. **メモリ最小**（ディスク 4.98 GB / 推論時 RAM 約 6 GB）— target mini PC（32 GB RAM）に最大の余裕を残す

### backup を Q5_K_M とする理由

- 品質は第一候補の **95%**（0.722 / 0.760）— backup 閾値 80% を大きく上回る
- 量子化階層が違う ため、将来 Q4 のモデル更新で問題が出ても Q5 が同時に壊れる可能性は低い
- 速度も実用域内（S2 58.5 秒）、ロード方法も同じで切替コストが低い

### Q8_0 を除外する理由

- 速度は最遅（S2 77.4 秒、Q4 比 +65%）
- 品質も Q5 と同等（0.716 vs 0.722）で、より重い割に得るものがない
- Q5 と比べても backup として優先する理由がない

---

## 2. 結果サマリ表

LM Studio、CPU-only、14 スレッド、median 値：

### 速度

| 量子化 | S2 wall (s) | S2 tok/s | S3 wall/画像 (s) | S3 tok/s | 失敗件数 |
|---|---|---|---|---|---|
| **Q4_K_M** | **46.8** | **14.8** | **81.9** | **14.6** | 0 |
| Q5_K_M | 58.5 | 12.8 | 89.5 | 12.7 | 0 |
| Q8_0 | 77.4 | 9.5 | 117.9 | 9.3 | 0 |

### 品質（Gemini 2.5 Flash judge による fact 単位スコア、0.0〜1.0）

| 量子化 | tc01 (24 件) | tc02 (20 件) | tc03 (26 件) | tc04 (22 件) | **平均** |
|---|---|---|---|---|---|
| **Q4_K_M** | 0.667 | **0.650** | **0.769** | 0.955 | **0.760** |
| Q5_K_M | 0.667 | 0.550 | 0.673 | **1.000** | 0.722 |
| Q8_0 | **0.708** | 0.450 | 0.750 | 0.955 | 0.716 |

生の judge 出力と fact ごとの verdict は [benchmarks/out/phase4/quality/](../../../benchmarks/out/phase4/quality/) を参照。

---

## 3. 評価セットアップ

- ホスト: LM Studio（Phase 3 勝者、`lms load --gpu off` で CPU-only 強制）
- モデルファミリー: HF `unsloth/gemma-4-E4B-it-GGUF` の **Gemma 4 E4B**
- 速度シナリオ:
  - S2: `samples/diagram.png`（3 回）
  - S3: `tests/text_vs_image/images/`（4 画像、各 1 回）
- 品質 source of truth: `tests/text_vs_image/test_cases.yaml`
- 品質テストケース: `tc01`, `tc02`, `tc03`, `tc04`
- 品質 judge: **Gemini 2.5 Flash**（外部 API）
- スコアリング規則: `present=1.0`、`partial=0.5`、`missing=0.0`
- 品質評価スクリプト: [tests/text_vs_image/phase4_quality_eval.py](../../../tests/text_vs_image/phase4_quality_eval.py)

### 量子化候補プール

| 量子化 | ファイル | LM Studio モデル ID | ロード alias | 備考 |
|---|---|---|---|---|
| Q4_K_M | 4.98 GB | `gemma-4-e4b-it@q4_k_m` | `gemma4-e4b-q4` | Phase 3 baseline、速度データ流用 |
| Q5_K_M | 5.48 GB | `gemma-4-e4b-it@q5_k_m` | `gemma4-e4b-q5` | Phase 4 で新規計測 |
| Q8_0 | 8.19 GB | `gemma-4-e4b-it@q8_0` | `gemma4-e4b-q8` | Phase 4 で新規計測 |
| FP16 / BF16 | 15.05 GB | （ロードせず） | — | 除外 — target mini PC に余裕が残らない |

3 量子化は同一の `mmproj-F16.gguf`（約 990 MB）vision projector を共有。

---

## 4. 結果から読み取れること

### 4.1 速度はファイルサイズに比例

CPU-only 推論ではメモリ帯域がボトルネック → 量子化サイズが直接スループットに反映：

- Q5_K_M は Q4_K_M より約 25% 遅い（10% 大きいファイル + 量子化デコード分のオーバーヘッド）
- Q8_0 は Q4_K_M より約 65% 遅い。S2 で 9.5 tok/s は「CPU 使用可能」水準のぎりぎり上

### 4.2 品質は 3 量子化とも統計的に区別不能

「量子化が軽ければ軽いほど品質が低い」という直感に反して、Q4 が平均トップ。これは「N=4 のテストセットでは差は judge 変動の範囲内」と読むのが妥当：

- 3 量子化の avg 差は 0.04 — これは judge（Gemini 2.5 Flash）自体の sampling variance の幅と同等
- tc02 が全量子化で最難（0.450〜0.650）— UI before/after 変化の列挙は苦手
- tc04 が全量子化で最易（0.955〜1.000）— 純テキスト OCR は Gemma 4 E4B の native 多言語 OCR の得意領域

### 4.3 選定ルールチェック

- ✅ 第一候補は品質の（タイ）トップ（0.760）
- ✅ 第一候補は S3 を完走（4/4 成功）
- ✅ 第一候補は最速（最速の 2 倍以内 → 自身が最速）
- ✅ Backup は第一候補品質の 80% 以上（95%）
- ✅ Backup は異なる量子化階層（Q4→Q5）で redundancy あり

---

## 5. 留保事項

- **N が小さい:** テストケース 4 件、fact 合計約 90 件。品質数値の sampling variance が大きい。10 ケース版にすれば比較がもっと締まる。
- **Judge は単一:** Gemini 2.5 Flash のみ。第 2 judge（Gemini 2.5 Pro 等別ファミリー）を加えると judge 固有の偏りが検出できる。
- **デフォルト sampling:** 3 量子化とも LM Studio のデフォルト `temperature` / `top_p` / `max_tokens` を使用。`temperature=0` の決定論的実行で 1 つのノイズ源を消せるが、絶対値は変わる可能性あり。
- **日本語プロンプトのみ:** `tc01..tc04` はいずれも日本語の質問。英語や混合言語のプロンプトでは未評価。

---

## 6. 次のアクション

Phase 6（target mini PC 検証）では Q4_K_M をインストールして実測する。Phase 4 の dev rig 値が target 実測値との比較 baseline となる。詳細は [04-target-validation.md](04-target-validation.md) を参照。
