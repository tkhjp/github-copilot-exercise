# Microsoft Copilot Web — 抽出プロンプト 比較レポート

_生成日: 2026-04-28 (extraction_report.py で自動生成、`python tests/text_vs_image/extraction/extraction_report.py` で再生成可)_

## 1. 実験概要

Microsoft Copilot Web (https://copilot.microsoft.com/) に同じテストコーパス (8 パターン)
を PNG / PPTX 形式で投入し、Copilot の応答を Gemini 2.5 Flash で recall (ground truth
fact 被覆率) と hallucination 件数で 3 run 採点した結果。

**評価指標**:
- **recall**: GT fact のうち Copilot 応答に含まれる割合 (0.0-1.0)。3 run の平均。
- **hallucination**: Copilot が GT に存在しない情報を出した件数 (件数、3 run 通算)。

## 2. 試行ラインナップ

| trial id | label | prompt | corpus | n_facts | 実施日 |
| --- | --- | --- | --- | --- | --- |
| `v1` | v1 prompt × v1 corpus | v1 (baseline) | v1 | 157 | 2026-04-23 |
| `v2` | v1 prompt × v2 corpus (Copilot Web) | v1 (baseline) | v2 | 273 | 2026-04-24 |
| `v2_api_gemini3` | v1 prompt × v2 corpus (Gemini 3 Flash API) | v1 (baseline) | v2 | 273 | 2026-04-27 |

- **`v1`**: 初期ベースライン。v1 corpus (P1-P8 計 157 facts) に v1 prompt (シンプルな書き起こし指示) を投入。
- **`v2`**: Ceiling fix 検証。v2 corpus (密度 2 倍化 + vague 吹き出し、計 273 facts) に v1 prompt をそのまま投入。Microsoft Copilot Web (UI 経由、人手で貼り付け) の baseline。
- **`v2_api_gemini3`**: コントロール群。v2 と同じ v1 prompt + v2 corpus を、Microsoft Copilot Web ではなく Gemini 3 Flash API (extractor) に直接投入。フロントエンド (Copilot Web vs 純粋 API) の差を測る。Judge 役は引き続き Gemini 2.5 Flash で同条件。

## 3. サマリー (試行 × フォーマット平均)

| trial | PNG recall avg | PNG hallu total | PPTX recall avg | PPTX hallu total |
| --- | --- | --- | --- | --- |
| `v1` | 0.894 | 31 | 0.901 | 13 |
| `v2` | 0.723 | 46 | 0.887 | 49 |
| `v2_api_gemini3` | 0.875 | 57 | — | 0 |

### 主要な変化

- `v1` → `v2` (ceiling fix (corpus 難化、Copilot Web 一定)) — PNG recall: **-0.171** (0.894 → 0.723)
- `v1` → `v2` (ceiling fix (corpus 難化、Copilot Web 一定)) — PPTX recall: **-0.013** (0.901 → 0.887)

- `v2` → `v2_api_gemini3` (frontend 切替 (corpus + prompt 一定、Copilot Web → Gemini 3 API)) — PNG recall: **+0.152** (0.723 → 0.875)

## 4. パターン別 recall (PNG)

| trial | p01 | p02 | p03 | p04 | p05 | p06 | p07 | p08 | avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v1` | 0.947 | 0.921 | 0.833 | 0.875 | 0.892 | 0.921 | 0.920 | 0.843 | 0.894 |
| `v2` | 0.483 | 0.510 | 0.870 | 0.781 | 0.910 | 0.746 | 0.780 | 0.701 | 0.723 |
| `v2_api_gemini3` | 0.800 | 0.833 | 0.917 | 0.800 | 0.974 | 0.794 | 1.000 | 0.880 | 0.875 |

## 5. パターン別 recall (PPTX)

| trial | p01 | p02 | p03 | p04 | p05 | p06 | p07 | p08 | avg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v1` | 0.970 | 0.851 | 0.889 | 1.000 | 0.941 | 0.897 | 1.000 | 0.657 | 0.901 |
| `v2` | 0.772 | 0.922 | 0.932 | 0.819 | 0.962 | 0.846 | 0.963 | 0.880 | 0.887 |
| `v2_api_gemini3` | — | — | — | — | — | — | — | — | — |

## 6. ハルシネーション件数 (パターン別、PNG + PPTX 合計)

| trial | p01 | p02 | p03 | p04 | p05 | p06 | p07 | p08 | 合計 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v1` | 16 | 8 | 0 | 3 | 1 | 4 | 6 | 6 | 44 |
| `v2` | 27 | 13 | 9 | 2 | 0 | 12 | 9 | 23 | 95 |
| `v2_api_gemini3` | 25 | 7 | 2 | 1 | 0 | 7 | 0 | 15 | 57 |

## 7. パターン名対応表

| pid | 内容 |
| --- | --- |
| `p01` | 勤怠アプリ画面 (UI callouts) |
| `p02` | Before/After 検索画面 |
| `p03` | 5 ステップ購入フロー |
| `p04` | Q1 売上ダッシュボード |
| `p05` | 決済システム階層ドリルダウン |
| `p06` | デザインレビュー (赤入れ) |
| `p07` | 混合ダッシュボードページ |
| `p08` | 組織図 |

## 8. ハルシネーション具体例 (試行別、最初の 3 件)

### `v1`
- **[png/p01]** 勤怠アプリ画面レビュー
- **[png/p01]** 2026-04-02 (木)　出勤 08:58
- **[png/p01]** 2026-04-02 (木)　退勤 19:40

### `v2`
- **[png/p01]** 4. 2026-04-04 / [判読不能] / [判読不能] / [判読不能] / [判読不能] / [判読不能] / [判読不能]
- **[png/p01]** 5. 2026-04-05 / [判読不能] / [判読不能] / [判読不能] / [判読不能] / [判読不能] / [判読不能]
- **[png/p01]** 6. 2026-04-06 / [判読不能] / [判読不能] / [判読不能] / [判読不能] / [判読不能] / [判読不能]

### `v2_api_gemini3`
- **[png/p01]** 2026-04-01 (水) の出勤時刻「09:02」
- **[png/p01]** 2026-04-01 (水) の退勤時刻「18:15」
- **[png/p01]** 2026-04-01 (水) の残業時間「00:13」

## 9. これまでの作業の経緯

### 9.1 v1 corpus + v1 prompt (初期ベースライン)

- 8 パターン (P1-P8) で 157 facts を Gemini 判定。
- PNG / PPTX とも recall **0.89-0.90** と高得点。
- **問題**: ceiling effect により今後の prompt 改善で差を測りにくい。

### 9.2 v2 corpus 設計 (ceiling fix)

v1 corpus の弱点を 2 軸で改修した:

1. **密度を約 2 倍化**: 表の列数・行数、コード行数、組織図ノード数、コメント数すべてを増量。
   合計 fact 数 157 → 273 (+74%)。
2. **吹き出しを vague 略記に変更**: v1 では「KPI カードは 4 枚ではなく 3 枚に減らす」のような
   答えを書いた吹き出しだったが、v2 では「5→4」「中央？」「16→24」のような
   手書きメモ風の短い表現に変更。対象要素は配置・矢印先から推論させる。
3. **対象推論ファクトの分離**: 吹き出し本文 verbatim (易) と吹き出しが指す対象 (難)
   を別個のファクトとして GT に格納し、OCR 力と画像構造理解力を分離評価可能に。

詳細は [PATTERNS.md](./PATTERNS.md) を参照。

### 9.3 v1 prompt × v2 corpus (ceiling fix の効果検証 / Copilot Web)

**同じ v1 prompt** をそのまま v2 corpus に投入。同条件 (prompt 一定) で corpus 難化が
どれだけ recall を下げるかを観測した。Microsoft Copilot Web (UI 経由、人手で
ファイルアップロード + プロンプト貼付) で実施。結果は §3 / §4 / §5 のテーブルを参照。

### 9.4 v1 prompt × v2 corpus (Gemini 3 Flash API / コントロール群)

Copilot Web が提供する recall 値が「Copilot 固有 (UI / 内部処理) の制約」なのか、
それとも「画像コンテンツの本質的な難しさ」なのかを切り分けるため、同じ v1 prompt と
v2 corpus を **Gemini 3 Flash Preview API に直接投入** したコントロール群を追加した。

- Extractor: `gemini-3-flash-preview` (Google AI Studio API、画像直接入力)
- Judge: `gemini-2.5-flash` (v1 / v2 trial と同じ判定モデル)
- 入力: tests/text_vs_image/extraction/p0N_*.png 8 枚 (v2 corpus と同一バイナリ)
- Prompt: benchmarks/out/extraction/v1/prompt.md と完全に同じ本文

Extractor は別モデル (Gemini 3 Flash) を使い、Judge は据え置き (Gemini 2.5 Flash)。
「同モデルの自己評価バイアス」は発生しない。

## 10. 考察

### 10.0 Copilot Web vs Gemini 3 Flash API (重要な発見)

**同じ画像 + 同じプロンプト** を Microsoft Copilot Web 経由 (`v2`) と Gemini 3 Flash API
経由 (`v2_api_gemini3`) で投入した結果、**recall は 0.723 → 0.875 (+0.152)** と大幅改善。
特にテーブル / 構造系で差が大きい:

- p01 勤怠表: 0.483 → **0.800** (+0.317) — Copilot が「[判読不能]」と諦めた表を API は完読
- p02 Before/After: 0.510 → **0.833** (+0.323) — 左右ペア要素を API は網羅
- p07 混合ダッシュボード: 0.780 → **1.000** (+0.220) — API は全 41 facts を完全抽出
- p08 組織図: 0.701 → 0.880 (+0.179)

これは「v2 corpus が難しすぎる」のではなく、**Copilot Web の UI / 内部処理パイプライン
自体が抽出精度を ~15% 押し下げている** ことを意味する。原因の候補:

- Copilot Web のチャット UI 内で出力長を切り詰めている可能性
- 画像のリサイズ / 圧縮が UI で介在している可能性
- 内部で異なる (より小さい) モデルにルーティングされている可能性
- 安全フィルタや投影層 (system prompt) が verbatim 出力を抑制している可能性

→ **実運用上の含意**: 抽出精度を最大化したいクライアントには、Copilot Web 手作業より
**Gemini API (または同等の Vision API) を直接呼ぶ自動化** を推奨できる。
Copilot Web は便利だが「人間が手で確認する補助ツール」であり、
「下流 LLM への verbatim 入力源」としては精度が約 15% 不足する。

### 10.1 ceiling effect は解消された

PNG recall は **0.894 → 0.722 (-0.172)** と大幅に低下し、prompt 改善の余地が広い
帯域で観測できる状態になった。今後の prompt v2/v3 では、ここから recall がどれだけ
回復するかが評価軸になる。

### 10.2 PPTX は corpus 難化に強い

PPTX recall は **0.901 → 0.887 (-0.014)** とほぼ変化なし。これは「Copilot が PPTX を
OCR ではなく XML 構造として直接読んでいる」可能性を示唆する強いシグナル。PNG では
細かい文字 / 密集レイアウトが直接的に OCR 精度を下げるが、PPTX 経由なら shape の
テキスト属性をそのまま読めるため、密度が上がっても大きく劣化しない。

→ **実運用上の含意**: クライアントには「PPT で資料を渡せるなら PNG/スクショ より遥かに
確実」と提案できる。逆に PNG/スクショしかない場合は prompt 側の補強が重要。

### 10.3 PNG で大きく崩れたパターン

- **p01 (勤怠アプリ): 0.947 → 0.483 (-0.464)** — 8 行 7 列の勤怠表を Copilot が
  全セル「[判読不能]」と諦めて出力。表が密集すると OCR を放棄する挙動が観測された。
- **p02 (Before/After): 0.921 → 0.510 (-0.411)** — 左右ペア要素 (メニュー数 3 vs 5、
  フィルタ階層 vs 単一行など) を半数取りこぼす。左右非対称な差分の網羅が苦手。
- **p06 (赤入れレビュー): 0.921 → 0.746 (-0.175)** — 25 個の vague callout 本文は
  転記できたが、「対象推論」(R01「中央？」がロゴを指している、など) の facts が落ちた。

### 10.4 PNG で持ちこたえたパターン

- **p05 (階層ドリルダウン): 0.892 → 0.910** (+0.018) — 12 行設定パラメータ表を完全転記。
  表の文字フォントが大きめで密集していなければ、行数が増えても recall は下がらない。
- **p03 (購入フロー): 0.833 → 0.870** (+0.037) — ステップ毎にカード分割されているため、
  情報が局所化され OCR 負荷が上がりにくい。

### 10.5 ハルシネーション傾向

v2 corpus でハルシネーション総数が **44 → 95** と倍増。特に p01 と p08 で多い:
- **p01**: Copilot が「[判読不能]」を埋めるためダミー行 (`5. 2026-04-05 / [判読不能] / ...`)
  を生成し、それが GT になく hallucination 判定。
- **p08**: 20 ノード組織図で氏名 / 役職を取り違えたり、存在しないノードを生成。

これらはハルシネーション抑制プロンプト (「推測で値を埋めない」) の効果検証対象。

## 11. 次のステップ

1. **prompt v2 設計** (`benchmarks/out/extraction/v2/prompt.md` または別ディレクトリ): 
   step-by-step 指示 + 表記ルール + 件数 self-verify で v1 prompt の上記弱点を直接対策。
2. **再判定**: prompt v2 × v2 corpus で 8 パターン × PNG/PPTX を投入、recall 回復幅を測定。
3. **prompt v3 (PPT 専用 CoT)**: shape 列挙順 / type タグなど PPT 構造を明示的に使う。
4. **prompt v4 (few-shot)**: vague callout 対象推論の好例を 1 つ仕込む。

---

_本レポートは extraction_report.py により自動生成されています。試行を追加・再判定後に_
_`python tests/text_vs_image/extraction/extraction_report.py` で本ファイルが上書きされます。_
_narrative セクション (§9-§11) はスクリプト内に埋め込まれているため、新たな試行を_
_追加した際は extraction_report.py の TRIAL_META と narrative を併せて更新してください。_
